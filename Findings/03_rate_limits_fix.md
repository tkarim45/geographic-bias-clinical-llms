# Claude Code Prompt 03 — Per-Model Rate-Limit Buckets

## Goal

The pilot lost 52/320 (16.3%) completions to Groq HTTP-429 "tokens-per-minute exceeded" errors, concentrated on Qwen3-32B and OpenAI-GPT-OSS-20B. The current `audit/models.py` uses **one token bucket per provider**, which lets a high-TPM model burn through the shared budget that other models on the same provider need.

OncQA at n=61 will trigger the same cascade unless this is fixed first.

## Read first

- `Module_3_Intermediate_Report/code/audit/models.py` — the entire file.
- Groq's rate-limit docs: the current free-tier limits vary per model (roughly 30 RPM / 6,000 TPM for large models, but stricter for Qwen-family).
- Check the latest pilot run directory's log for the exact 429 response bodies — they contain the precise TPM limit Groq is enforcing.

## Tasks

### Task 1 — Inspect current implementation (10 min)

```bash
cd Module_3_Intermediate_Report/code
grep -n "TokenBucket\|rate_limit\|RPM\|TPM\|429" audit/models.py
```

Understand:
- Is there one `TokenBucket` per `Client` instance?
- Are `Client` instances keyed by provider or by model?
- Where is the refill rate set?

Write your findings as comments at the top of the replacement patch.

### Task 2 — Design the per-model bucket scheme (20 min)

Target config (verify against Groq current pages; adjust if they've changed):

| Model | RPM | TPM | Notes |
|---|---|---|---|
| openai/gpt-4o-mini (OpenAI direct) | 60 | — | Tier 1 default |
| groq/meta-llama/llama-3.3-70b-versatile | 10 | 6,000 | Free tier |
| groq/openai/gpt-oss-20b | 5 | 3,000 | More conservative — this model had ~19 losses |
| groq/qwen/qwen3-32b | 5 | 3,000 | Most conservative — ~33 losses |
| groq/llama-3.1-8b-instant (annotator) | 15 | 6,000 | Must not be starved by main models |

Critical: the annotator and main-model calls currently share the Groq budget. Reserve the annotator bucket **separately** from the main-model buckets so re-annotation doesn't starve generation (or vice versa).

### Task 3 — Implement (60 min)

In `audit/models.py`:

1. Replace the provider-keyed bucket dict with a model-keyed one:

```python
# Before (pseudocode):
#   _buckets = {"openai": TokenBucket(...), "groq": TokenBucket(...)}
# After:
_buckets: dict[str, TokenBucket] = {}

_RATE_LIMITS = {
    "openai/gpt-4o-mini": {"rpm": 60, "tpm": None},
    "openai/gpt-4.1-mini": {"rpm": 60, "tpm": None},  # forward-compat
    "groq/meta-llama/llama-3.3-70b-versatile": {"rpm": 10, "tpm": 6000},
    "groq/openai/gpt-oss-20b": {"rpm": 5, "tpm": 3000},
    "groq/qwen/qwen3-32b": {"rpm": 5, "tpm": 3000},
    "groq/llama-3.1-8b-instant": {"rpm": 15, "tpm": 6000},  # annotator
}

def _bucket_for(model_id: str) -> TokenBucket:
    if model_id not in _buckets:
        spec = _RATE_LIMITS.get(model_id, {"rpm": 10, "tpm": 6000})  # safe default
        _buckets[model_id] = TokenBucket(rpm=spec["rpm"], tpm=spec["tpm"])
    return _buckets[model_id]
```

2. Ensure `TokenBucket` supports **both** RPM and TPM simultaneously. If the current implementation only limits RPM, add token-count tracking:

```python
class TokenBucket:
    def __init__(self, rpm: int, tpm: int | None = None):
        self.rpm = rpm; self.tpm = tpm
        self._req_times: list[float] = []
        self._tok_events: list[tuple[float, int]] = []   # (t, token_count)
        self._lock = threading.Lock()

    def acquire(self, expected_tokens: int = 800):
        while True:
            with self._lock:
                now = time.monotonic()
                # Expire entries older than 60s
                self._req_times = [t for t in self._req_times if now - t < 60]
                self._tok_events = [(t, n) for (t, n) in self._tok_events if now - t < 60]
                tokens_used = sum(n for _, n in self._tok_events)
                if (len(self._req_times) < self.rpm
                    and (self.tpm is None or tokens_used + expected_tokens <= self.tpm)):
                    self._req_times.append(now)
                    self._tok_events.append((now, expected_tokens))
                    return
            time.sleep(0.25)

    def record_actual_tokens(self, actual: int, expected: int):
        """Adjust the most recent event if actual differs materially."""
        if abs(actual - expected) < 100:
            return
        with self._lock:
            if self._tok_events:
                t, _ = self._tok_events.pop()
                self._tok_events.append((t, actual))
```

3. After each successful API call, call `bucket.record_actual_tokens(response_usage_total, 800)` to correct the estimate for the next round.

### Task 4 — Add a retry-aware 429 handler (30 min)

The current retry loop backs off exponentially but does not *learn* from the 429 `Retry-After` header or the response body (which sometimes says "Please try again in 42.1 seconds").

Add:

```python
def _parse_retry_after(response_body: str, headers: dict) -> float | None:
    # Honour standard header first
    if "retry-after" in headers:
        try: return float(headers["retry-after"])
        except ValueError: pass
    # Fallback: parse "try again in Xs" from Groq's body
    import re
    m = re.search(r"try again in ([\d.]+)s", response_body, re.I)
    if m: return float(m.group(1))
    return None
```

In the retry loop, prefer `parse_retry_after()` result over exponential backoff. Also: after a 429, **drain** the relevant bucket so subsequent calls wait properly:

```python
retry = _parse_retry_after(body, resp_headers)
if retry:
    time.sleep(retry + 1.0)  # +1s safety margin
else:
    time.sleep(2 ** attempt + random.random())
```

### Task 5 — Run the pilot config again as a regression test (15 min)

```bash
python3 -m audit.run --config configs/pilot_oncqa.yaml --seed 42 --parallelism 4
```

Expected: 320 completions, **zero** annotator heuristic fallbacks (cache means no new generation billing on same model/prompt/seed, but new rate limiter will still govern the annotator calls).

Acceptance: completions_total == 320 and rate_limit_errors_total == 0 in the run's log or summary.

### Task 6 — Document in `decisions.md`

```
## Rate-limit infrastructure fix (prompt 03)

- Changed _buckets from provider-keyed to model-keyed
- Added per-model RPM/TPM limits in _RATE_LIMITS
- Annotator has its own bucket (groq/llama-3.1-8b-instant)
- Retry handler now honours Groq's "try again in Xs" body / Retry-After header
- Regression test: pilot config at n=20 with 0 rate-limit errors (was 52/320)
```

## Deliverables

- [ ] Patched `audit/models.py`
- [ ] Passing regression run on pilot config (0 rate-limit errors)
- [ ] `decisions.md` entry

## What NOT to do

- Do not aggressively raise limits. Prefer headroom over throughput; 60-hour wall-clock for the full experiment is acceptable.
- Do not touch the retry count (stay at 5). The fix is *better* throttling, not more retries.
- Do not change the annotator prompt. That belongs to a separate concern.

## Success criterion

A re-run of `configs/pilot_oncqa.yaml` produces 320/320 completions with 0 heuristic annotator fallbacks, within ~12 min wall time (slower than before, but reliable).

## Why this is critical-path

Every subsequent run (OncQA in prompt 01, ablations in prompt 02, multi-seed in final-report scope) depends on this. Without it, every large run burns hours on retries for losses that never recover.
