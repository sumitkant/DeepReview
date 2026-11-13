---
name: deep-review
description: Deep multi-stage review of a dense document (paper, resume, blog post, contract, report). Segments the document, runs parallel reviewer subagents, checks every quote in code, verifies each finding with an independent subagent, grounds outside facts by web search, and writes severity-ranked comments anchored to exact quotes plus an annotated HTML report. Use when the user asks for a deep review, expert feedback, error hunting, or "review this like Deep Review".
---

# Deep review

`ROOT` is the plugin root: the folder that holds `prompts/`, `profiles/` and `scripts/` (`${CLAUDE_PLUGIN_ROOT}` when set, otherwise two levels above this file). Read each stage prompt from `ROOT/prompts/` when you reach its stage and follow it exactly, including its JSON shape.

Inputs: a document path. Optional: author context (what the document is for), a profile, and depth (`low`, `mid`, `high`, `extra_high`; default `mid`). With no author context, review the document on its own terms and do not judge fit to an outside goal.

Work in `<document folder>/review_<document name>/` and save every stage's file there.

1. **Extract.** Write the document as UTF-8 text with `[page N]` markers to `document.txt`. For a PDF also read the rendered pages, so layout is judged from the page and not from extraction artifacts.
2. **Profile.** Use the matching file in `ROOT/profiles/` (`resume.md`, `research-paper.md`, `technical-blog.md`). For another document type, write a profile of the same shape (what counts as an error, a gap, a clarity issue) and save it as `profile.md`.
3. **Ledger.** Apply `prompts/0_ledger.md` yourself: the thesis, the core claims with evidence and warrant, the load-bearing claims, and the claim/evidence mismatches. Save `0_ledger.json`.
3b. **Segment.** Apply `prompts/1_segmenter.md` with the ledger. Save `1_segments.json`. It must include `global-consistency` and `copy-consistency` segments, and every load-bearing claim and mismatch must appear in some segment's checks.
4. **Review in parallel.** Launch one subagent per segment pass, all in one message. Each reads `prompts/2_reviewer.md`, the profile, the author context, `0_ledger.json`, `document.txt`, the original file, and its segment, and writes `2_review_<id>.json`. Give subagents file paths and their segment only, never your own view of the document. Passes per segment:

   | depth | light | medium | high |
   |---|---|---|---|
   | low | 1 | 1 | 1 |
   | mid | 1 | 1 | 2 |
   | high | 1 | 2 | 3 |
   | extra_high | 2 | 3 | 5 |

   A second or later pass on a segment is told to work through it in reverse order and to concentrate on the reasoning behind each claim.
5. **Ground.** While reviewers run, web-search every item in `external_checks`; when they finish, search every finding with `needs_external_check`. Save what each source says, with its URL, to `search_results.md`. List what you did not check.
6. **Gates in code.** Run `python "ROOT/scripts/apply_gates.py" "<review folder>"`. It merges all reviewer files into `2_findings.json` and applies both gates: Drop every finding whose `quote` is not in `document.txt` (compare with whitespace collapsed, case-insensitive). Then apply the admission gate: any CRITICAL or MAJOR finding with an empty `verification.action`, `verification.outcome` or `impact` gets `needs_verification: true`, and any finding with `needs_verification` true is capped at MINOR. Report how many were dropped and how many were capped.
7. **Verify.** Launch one fresh subagent with `prompts/3_verifier.md`, the profile, `document.txt`, the original file, `2_findings.json` and `search_results.md`. Save `3_verdicts.json`.
8. **Synthesize.** Apply `prompts/4_synthesizer.md`: drop rejected findings, merge duplicates, apply the verifier's corrected severity, label, body and edit, order by page. Save `4_review.json` (`review_markdown` plus `anchored_comments`) and `review.md`.
9. **Render.** Run the `review-html` skill's command to produce `review.html`, and tell the user where it is.

Rules that hold in every stage:
- No finding without an exact quote. No new findings at synthesis.
- Nothing is rated CRITICAL or MAJOR without a named check, its outcome and a stated impact. Unconfirmed findings are kept, flagged `needs_verification`, and shown as "Needs verification", never as established.
- Extraction artifacts (split words, line-end hyphens, reordered lines, lost icons) are never findings.
- Outside facts are stated only from `search_results.md` or as well-established facts of the field; everything else is marked unverified.
- Suggested edits never add a fact the document does not contain; use `[placeholders]`.
- No scores and no accept or reject verdict.
- Report honestly at the end: counts at each stage, what was rejected, what was not checked.
