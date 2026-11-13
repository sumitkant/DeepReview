#!/usr/bin/env python3
"""Deep review pipeline: claim ledger -> segment -> parallel review -> gates in code -> verify -> synthesize.

Standard library only. Talks to any OpenAI-compatible /chat/completions endpoint:
OpenAI, Azure OpenAI, Gemini (OpenAI-compat endpoint), GitHub Models, Ollama, LM Studio.

  set OPENAI_API_KEY=...            (not needed for Ollama)
  set OPENAI_BASE_URL=https://api.openai.com/v1
  python deep_review.py doc.pdf --profile profiles/resume.md --context context.md \
      --model gpt-5 --depth mid --out output/run1
"""
import argparse, concurrent.futures as cf, json, os, pathlib, re, subprocess, sys, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
if not (HERE / "prompts").exists():  # plugin layout: scripts/ sits beside prompts/ and profiles/
    HERE = HERE.parent
# depth = Deep Review's "topology": independent reviewer passes per segment, by segment budget.
DEPTH = {
    "low": {"light": 1, "medium": 1, "high": 1},
    "mid": {"light": 1, "medium": 1, "high": 2},
    "high": {"light": 1, "medium": 2, "high": 3},
    "extra_high": {"light": 2, "medium": 3, "high": 5},
}


def read_document(path):
    p = pathlib.Path(path)
    if p.suffix.lower() != ".pdf":
        return p.read_text(encoding="utf-8")
    try:
        from pypdf import PdfReader
        return "\n".join(f"[page {i + 1}]\n{pg.extract_text()}" for i, pg in enumerate(PdfReader(str(p)).pages))
    except ImportError:
        return subprocess.run(["pdftotext", "-enc", "UTF-8", str(p), "-"], capture_output=True, check=True).stdout.decode("utf-8")


def llm(system, user, args):
    body = {"model": args.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}}
    if args.effort:
        body["reasoning_effort"] = args.effort  # Deep Review's "thinking level"
    req = urllib.request.Request(
        args.base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "none")})
    with urllib.request.urlopen(req, timeout=args.timeout) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)  # tolerate ```json fences
    return json.loads(m.group(0) if m else text)


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("document")
    ap.add_argument("--profile", default=str(HERE / "profiles" / "research-paper.md"))
    ap.add_argument("--context", help="file with author context (Deep Review's 'custom context')")
    ap.add_argument("--search", help="file with outside evidence to ground against (optional)")
    ap.add_argument("--model", default=os.environ.get("DEEP_REVIEW_MODEL", "gpt-5"))
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--depth", choices=DEPTH, default="mid")
    ap.add_argument("--effort", choices=["low", "medium", "high"], help="reasoning effort, if the model supports it")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", default="output/run")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    save = lambda name, obj: (out / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    prompt = lambda n: (HERE / "prompts" / n).read_text(encoding="utf-8")
    doc = read_document(args.document)
    opt = lambda p: pathlib.Path(p).read_text(encoding="utf-8") if p else "(none)"
    common = (f"REVIEW PROFILE:\n{pathlib.Path(args.profile).read_text(encoding='utf-8')}\n\n"
              f"AUTHOR CONTEXT:\n{opt(args.context)}\n\nDOCUMENT:\n{doc}\n\n")

    # Stage 0: claim-evidence ledger
    ledger = llm(prompt("0_ledger.md"), common, args)
    save("0_ledger.json", ledger)
    common += "CLAIM LEDGER:\n" + json.dumps(ledger) + "\n\n"

    # Stage 1+2: segmentation and budgets
    plan = llm(prompt("1_segmenter.md"), common, args)
    save("1_segments.json", plan)
    print(f"segments: {len(plan['segments'])}", file=sys.stderr)

    # Stage 3: parallel deep review, k passes per segment by budget
    jobs = [(s, i) for s in plan["segments"] for i in range(DEPTH[args.depth].get(s.get("budget", "medium"), 1))]
    review = lambda job: llm(prompt("2_reviewer.md"), common + "YOUR SEGMENT:\n" + json.dumps(job[0]), args).get("findings", [])
    with cf.ThreadPoolExecutor(args.workers) as ex:
        findings = [dict(f, segment_id=job[0]["id"]) for job, fs in zip(jobs, ex.map(review, jobs)) for f in fs]

    # Deterministic hallucination guard: the quote must exist in the document
    ndoc = norm(doc)
    for f in findings:
        f["quote_found"] = norm(f.get("quote", "")) in ndoc and bool(f.get("quote"))
    findings = [f for f in findings if f["quote_found"]] or findings
    # Admission gate: no CRITICAL/MAJOR without a named check, its outcome, and a stated impact
    for f in findings:
        v = f.get("verification") or {}
        gate = bool(str(v.get("action", "")).strip() and str(v.get("outcome", "")).strip() and str(f.get("impact", "")).strip())
        if f.get("severity") in ("CRITICAL", "MAJOR") and not gate:
            f["needs_verification"] = True
        if f.get("needs_verification") and f.get("severity") in ("CRITICAL", "MAJOR"):
            f["severity"] = "MINOR"
    save("2_findings.json", findings)
    print(f"findings after quote check: {len(findings)}", file=sys.stderr)

    # Stage 3b: independent verification
    verdicts = llm(prompt("3_verifier.md"),
                   common + f"FINDINGS:\n{json.dumps(findings)}\n\nSEARCH RESULTS:\n{opt(args.search)}", args).get("verdicts", [])
    for v in verdicts:
        if isinstance(v.get("index"), int) and 0 <= v["index"] < len(findings):
            findings[v["index"]]["verdict"] = v
    save("3_verified.json", findings)

    # Stage 4: synthesis
    final = llm(prompt("4_synthesizer.md"),
                common + f"VERIFIED FINDINGS:\n{json.dumps(findings)}\n\nSEARCH RESULTS:\n{opt(args.search)}", args)
    save("4_review.json", final)
    (out / "review.md").write_text(final.get("review_markdown", ""), encoding="utf-8")
    print(f"wrote {out / 'review.md'} ({len(final.get('anchored_comments', []))} comments)", file=sys.stderr)
    try:  # annotated HTML; PDF input needs PyMuPDF
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import render_review
        render_review.main(args.document, str(out / "4_review.json"), str(out / "review.html"))
    except SystemExit as e:
        print(f"HTML not rendered: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
