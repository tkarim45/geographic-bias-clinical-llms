"""
Cohen's kappa between two sets of binary labels for each of the three
audit questions: MANAGE, VISIT, RESOURCE.

Accepts two JSONL files whose records have a `case_id` key and a `gold`
object (lowercase: {"manage": 0|1, "visit": 0|1, "resource": 0|1}). Records
whose gold is null (UNCLEAR) are excluded from that question's computation.

Usage:
    python3 scripts/compute_kappa.py --a configs/cases_labels_A.jsonl \\
                                     --b configs/cases_labels_B.jsonl

Writes a JSON summary to stdout and to --out if provided.
"""

import argparse
import json
import sys
from pathlib import Path

QUESTIONS = ("manage", "visit", "resource")


def cohens_kappa(y1, y2):
    assert len(y1) == len(y2)
    n = len(y1)
    if n == 0:
        return float("nan")
    agree = sum(a == b for a, b in zip(y1, y2))
    po = agree / n
    p1_0 = y1.count(0) / n
    p1_1 = y1.count(1) / n
    p2_0 = y2.count(0) / n
    p2_1 = y2.count(1) / n
    pe = p1_0 * p2_0 + p1_1 * p2_1
    if pe >= 1.0:
        return 1.0 if po == 1.0 else float("nan")
    return (po - pe) / (1 - pe)


def load(path):
    records = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        cid = rec["case_id"]
        gold = rec.get("gold")
        records[cid] = gold
    return records


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a", required=True, help="labeller A JSONL")
    p.add_argument("--b", required=True, help="labeller B JSONL")
    p.add_argument("--out", default=None, help="optional JSON output path")
    args = p.parse_args()

    A = load(args.a)
    B = load(args.b)
    common_ids = sorted(set(A) & set(B))

    summary = {
        "labeller_a": args.a,
        "labeller_b": args.b,
        "n_common": len(common_ids),
        "per_question": {},
    }

    for q in QUESTIONS:
        y1, y2, kept_ids, dropped = [], [], [], []
        for cid in common_ids:
            ga, gb = A[cid], B[cid]
            if ga is None or gb is None or q not in ga or q not in gb:
                dropped.append(cid)
                continue
            y1.append(int(ga[q]))
            y2.append(int(gb[q]))
            kept_ids.append(cid)
        n = len(y1)
        agree = sum(a == b for a, b in zip(y1, y2))
        kappa = cohens_kappa(y1, y2)
        summary["per_question"][q] = {
            "n": n,
            "agreement_count": agree,
            "agreement_rate": (agree / n) if n else None,
            "kappa": kappa,
            "dropped_case_ids": dropped,
        }

    print(json.dumps(summary, indent=2, default=str))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
