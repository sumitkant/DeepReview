# deep-review-kit: workbench

This folder holds the working files behind the pipeline in `../deep-review-plugin/`: every intermediate file from the example runs, and the notes on what is publicly known about Google's Deep Review. To use the pipeline, go to `../deep-review-plugin/README.md`.

## Example runs

```
output/blog/       first run on the example post (done before Google's review of it was seen)
output/blog_v2/    second run, with the claim ledger, admission gate and verification category
```

| File | Stage |
|---|---|
| `document.txt` | extracted text with page markers |
| `0_ledger.json` | claim ledger (v2 only) |
| `1_segments.json` | segments, budgets and checks |
| `2_review_*.json` | each reviewer's raw output |
| `2_findings.json` | merged findings after the code gates |
| `search_results.md` | outside evidence with URLs |
| `3_verdicts.json`, `3_verified.json` | the verifier's verdict on each finding |
| `4_review.json` | final review; the input to the HTML page |
| `review.md` | final review as text |
| `build_review.py` | the merge script the synthesizer wrote (v2 only) |
| `comparison_with_google.md` | this pipeline against Google's review of the same post (first run) |

## What is known about Google's Deep Review, and from where

Google's prompts, agent files and orchestration code run on Google's servers and are not published. The web page ships only a UI bundle and the paper has no prompt appendix. Nothing here is extracted from Google.

| Fact | Source |
|---|---|
| Four stages: document segmentation, adaptive budgeting, deep review, global synthesis | Paper, Fig. 1 (arXiv 2606.28277) |
| A segmenter splits the document into thematic segments that may overlap and be non-contiguous, and gives each a compute budget (light, medium, high thinking) by density and complexity | Paper, section 2 |
| One review agent per segment; each sees the full document but is responsible only for its segment | Paper, section 2 |
| A synthesis agent de-duplicates, checks severity, and uses Google Search to catch hallucinated papers and theorems | Paper, section 2 and Fig. 1 |
| No scores or accept/reject; objective errors and improvements only | Paper, section 2 |
| "Review depth" is how many multi-agent review and verification passes run (LOW, MID, HIGH, EXTRA_HIGH). "Thinking level" is reasoning effort per model call | FAQ; API discovery document |
| A free-text custom context is accepted | API `DeepReviewRunConfig` |
| Output: up to 300 anchored comments (severity CRITICAL, MAJOR, MINOR or SUGGESTION, summary, body, suggested edit, quote-anchored location) plus an overall review, and a per-reference citation report | API `Result`, `AnchoredReviewComment`, `CitationReport` |
| Reported failure modes: date and knowledge-cutoff errors, PDF parsing, false claims that a correct argument is wrong | Paper, section 3.2 |

## Reconstruction choices that Google has not confirmed

- The wording of every prompt.
- Mapping depth to independent reviewer passes per segment, scaled by budget.
- A separate adversarial verifier stage. The FAQ says verification passes exist; where they sit is a guess.
- The quote check and the admission gate in code.
- Review profiles per document type, standing in for Google's unpublished domain prompts.
- The claim ledger, named factual checks, verification category and opponent reading, which come from DeepReviewer 2.0, not from Google.
- No per-reference citation checker yet. The API schema above shows the fields Google reports for one.
