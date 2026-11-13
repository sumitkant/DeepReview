#!/usr/bin/env python3
"""Merge reviewer outputs and apply the two code gates.

    python apply_gates.py RUN_FOLDER

Reads RUN_FOLDER/document.txt and every RUN_FOLDER/2_review_*.json, writes RUN_FOLDER/2_findings.json.

Gate 1 (quote): a finding whose quote is not in document.txt is dropped.
Gate 2 (admission): a CRITICAL or MAJOR finding without a named check, its outcome and a stated
impact is flagged needs_verification; any needs_verification finding is capped at MINOR.
"""
import glob, json, os, re, sys


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def main(folder):
    doc = norm(open(os.path.join(folder, "document.txt"), encoding="utf-8").read())
    kept, dropped, capped = [], [], 0
    for path in sorted(glob.glob(os.path.join(folder, "2_review_*.json"))):
        data = json.load(open(path, encoding="utf-8"))
        for f in data.get("findings", []):
            f["segment_id"] = data.get("segment_id", os.path.basename(path))
            q = norm(f.get("quote"))
            if not q or q not in doc:
                dropped.append((f["segment_id"], (f.get("quote") or "")[:70]))
                continue
            v = f.get("verification") or {}
            gate = all(str(x or "").strip() for x in (v.get("action"), v.get("outcome"), f.get("impact")))
            f["severity"] = str(f.get("severity", "MINOR")).upper()
            if f["severity"] in ("CRITICAL", "MAJOR") and not gate:
                f["needs_verification"] = True
                f["gate_note"] = "admission gate: missing verification action, outcome or impact"
            if f.get("needs_verification") and f["severity"] in ("CRITICAL", "MAJOR"):
                f["severity_before_gate"], f["severity"] = f["severity"], "MINOR"
                capped += 1
            kept.append(f)
    for i, f in enumerate(kept):
        f["index"] = i
    json.dump(kept, open(os.path.join(folder, "2_findings.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"{len(kept)} findings kept, {len(dropped)} dropped by the quote gate, {capped} capped by the admission gate, "
          f"{sum(bool(f.get('needs_verification')) for f in kept)} flagged needs_verification")
    for seg, q in dropped:
        print(f"  dropped [{seg}]: {q}".encode("ascii", "replace").decode())


if __name__ == "__main__":
    main(sys.argv[1])
