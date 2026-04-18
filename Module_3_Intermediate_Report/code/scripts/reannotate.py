"""Re-annotate the heuristic-fallback records one at a time with a long
inter-call sleep to stay inside Groq's TPM limit. Reuses the response cache
from the run. Updates annotated.jsonl in place.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit.annotate import annotate as annotate_text  # noqa: E402
from audit.models import ResponseCache  # noqa: E402
from audit.metrics import compute_model_gdi  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--sleep", type=float, default=10.0,
                    help="Seconds to sleep between annotator calls (default 10).")
    ap.add_argument("--max-calls", type=int, default=0,
                    help="Limit re-annotation to N calls (0 = all).")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    annotated_path = run_dir / "annotated.jsonl"
    cache = ResponseCache(run_dir / ".cache")

    recs = [json.loads(l) for l in annotated_path.read_text().splitlines() if l.strip()]
    targets = [i for i, r in enumerate(recs)
               if r.get("annotator_heuristic") and r.get("text")]
    print(f"Loaded {len(recs)} records; {len(targets)} need re-annotation.")

    done = 0
    for idx in targets:
        if args.max_calls and done >= args.max_calls:
            break
        rec = recs[idx]
        try:
            labels = annotate_text(rec["text"], cache=cache, seed=42)
        except Exception as e:  # noqa: BLE001
            print(f"  [skip {idx}] annotator error: {e}")
            time.sleep(args.sleep)
            continue

        if labels.get("_heuristic"):
            # still failed; leave alone
            print(f"  [skip {idx}] still heuristic-fallback")
        else:
            rec["labels"] = {k: labels[k] for k in ("manage", "visit", "resource")}
            rec["annotator_raw"] = labels.get("raw", "")
            rec["annotator_heuristic"] = False
            done += 1
            if done % 5 == 0:
                print(f"  re-annotated {done}/{len(targets)}")
        time.sleep(args.sleep)

    # Write updated annotations atomically
    tmp = annotated_path.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(r) for r in recs))
    tmp.rename(annotated_path)
    print(f"Wrote {annotated_path}; {done} re-annotated successfully.")

    # Recompute metrics
    print("Recomputing summaries ...")
    n_south = sum(1 for r in recs if r["region"] != "global_north")
    summaries = compute_model_gdi(recs, n_south_regions=3)
    (run_dir / "summaries.json").write_text(json.dumps(summaries, indent=2))
    print()
    print("=" * 78)
    print(f"{'Model':42} {'RCER_N':>8} {'RCER_S':>8} {'Δ':>7} {'GDI':>7} {'p':>7}")
    print("-" * 78)
    for s in summaries:
        rn = sum(s["rcer_north"].values()) / 3
        rs = sum(s["rcer_south"].values()) / 3
        print(f"{s['model']:42} {rn*100:>7.1f}% {rs*100:>7.1f}% "
              f"{(rs-rn)*100:>+6.1f}pp {s['gdi']:>7.3f} {s['wilcoxon_p_greater']:>7.3f}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
