# DeepReview

A staged, multi-agent review pipeline for dense documents: papers, technical posts, resumes, reports. It finds factual errors, contradictions, unsupported claims and typos, shows them on an annotated HTML page next to the passages they refer to, and rewrites the document from the comments you accept.

It is an independent reconstruction of the approach behind Google's Deep Review, written from Google's public paper, FAQ and API schema, with several ideas taken from DeepReviewer 2.0. It runs on Claude Code, GitHub Copilot, ChatGPT, or any OpenAI-compatible API.

## Features

**Review**
- **Claim ledger first.** Before reviewing, the pipeline writes down the document's thesis, its core claims, the evidence behind each, and which claims the whole document depends on. Reviewers push hardest on those.
- **Parallel reviewers.** The document is split into segments; one reviewer per segment, each with the full document for context. Dense segments can get extra passes.
- **Opponent reading.** Reviewers assume the document is wrong and look for the simpler explanation.
- **Six named factual checks**: numbers, text against tables and code, setup consistency, measure against claim, cause, outside facts.
- **Proofreading pass** over the whole document, one comment per slip with the corrected sentence.
- **Web grounding** for facts that can only be checked outside the document, with the source URL on the comment.

**Precision**
- **Every comment quotes the document exactly.** A finding whose quote cannot be found is dropped in code.
- **Admission gate, in code.** Nothing is rated critical or major without a named check, its outcome and a stated impact.
- **Independent verifier.** A fresh reviewer re-checks every finding, corrects or rejects it, and rejects anything that is only a PDF-extraction artifact.
- **"Needs verification" is its own category.** Findings that could not be confirmed are shown as such, never as established.
- **No invented facts.** Suggested fixes use `[placeholders]` for anything only the author knows.
- **No scores and no accept or reject verdict.**

**Report**
- **One self-contained HTML page.** The document on the left with each passage highlighted, the comments on the right; click either to jump to the other.
- **Summary at the top**: findings, must fix, minor, can ignore, needs verification. Each count is colour coded and filters the page.
- **Accept or Dismiss each comment**, add a note, and export your decisions as JSON.
- Light and dark themes.

**Rewrite**
- Applies only the comments you accepted, honours your notes, leaves the rest of the document alone.
- Returns the revised document, a change log, and a list of facts it still needs from you.

## How it works

```
document
   │
   ▼
0 ledger ──► 1 segment ──► 2 review (parallel) ──► gates in code ──► web grounding
                                                                          │
   review.html ◄── render ◄── 4 synthesize ◄── 3 verify (independent) ◄───┘
        │
        ▼  you accept or dismiss, then export decisions
   5 rewrite ──► revised document + change log + facts still needed
```

## Use it

Everything you install is in `deep-review-plugin/`. The HTML step needs PyMuPDF for PDF input:

```bash
pip install pymupdf
```

### Claude Code

```
/plugin marketplace add /path/to/DeepReview/deep-review-plugin
```
```
/plugin install deep-review@deep-review-local
```

Then ask in plain words:

- "Deep review `my-paper.pdf`"
- "Make the HTML report for that review"
- "Apply the review" (after you export `review_decisions.json` from the page)

### GitHub Copilot (VS Code)

Open `deep-review-plugin/` as the workspace, or copy its `.github/`, `skills/`, `prompts/`, `profiles/` and `scripts/` folders into yours. In agent mode run `/deep-review`, `/review-html` or `/review-rewrite`, or pick the `deep-review` agent.

### ChatGPT

ChatGPT has no local plugin format, so this is a Custom GPT. Follow `deep-review-plugin/chatgpt/custom-gpt-instructions.md`: paste the instructions, upload the prompts, profiles and `render_review.py` as knowledge files, and turn on web search and code interpreter.

### Any OpenAI-compatible API, no agent

```bash
python deep-review-plugin/scripts/deep_review.py my-doc.pdf --profile deep-review-plugin/profiles/technical-blog.md --depth mid --out review_my-doc
```

Set `OPENAI_API_KEY` and, for other providers, `OPENAI_BASE_URL`. This mode does not search the web; pass your own evidence file with `--search`.

### Render a review you already have

```bash
python deep-review-plugin/scripts/render_review.py my-doc.pdf review_my-doc/4_review.json review_my-doc/review.html
```

## Options

| Option | Values | Effect |
|---|---|---|
| Depth | `low`, `mid`, `high`, `extra_high` | Reviewer passes per segment; more passes find more and cost more |
| Profile | `resume`, `research-paper`, `technical-blog`, or your own | What counts as an error for this kind of document |
| Author context | free text | What the document is for. Without it, the document is reviewed on its own terms |

To add a document type, copy a file in `deep-review-plugin/profiles/` and edit the three lists: errors, gaps, clarity issues.

## Reading the report

| Category | Meaning |
|---|---|
| Must fix | Critical and major: factual errors, contradictions, unsupported central claims |
| Minor | Typos, small inconsistencies, loose wording |
| Can ignore | Optional suggestions; the document is not wrong without them |
| Needs verification | The pipeline could not confirm it; check before acting |

Mark each comment Accept or Dismiss, add a note where a fix needs a fact from you, and press "Export decisions". Give the saved `review_decisions.json` to the rewrite step.

## Example

`review2/` holds a 15-page technical blog post and two reviews of it produced by this pipeline. Open `review2/kit_review_v2.html` in a browser. The intermediate files of each run (ledger, segments, every reviewer's raw output, the verifier's verdicts) are in `deep-review-kit/output/blog/` and `blog_v2/`.

## Repository layout

```
deep-review-plugin/        what you install
  prompts/                 0_ledger  1_segmenter  2_reviewer  3_verifier  4_synthesizer  5_rewriter
  profiles/                resume  research-paper  technical-blog
  scripts/                 render_review.py  apply_gates.py  deep_review.py  extract_google_review.py
  skills/                  Claude Code: deep-review, review-html, review-rewrite
  .claude-plugin/          Claude Code plugin and local marketplace manifests
  .github/                 GitHub Copilot prompt files and agent
  chatgpt/                 Custom GPT instructions
  README.md                install details, limits, test status
deep-review-kit/           workbench
  output/blog, blog_v2/    every intermediate file from the example runs
  README.md                what is publicly known about Google's pipeline, with sources
review2/                   example document and its rendered reviews
```

## Limits and status

- **Not Google's prompts.** Google's are not public. These were written from public descriptions and adjusted after comparing with two real Deep Review outputs. On a blind test, this pipeline found 13 of Google's 28 comments on the example post, 10 in part, missed 5, and raised about a dozen points Google did not. See `deep-review-kit/output/blog/comparison_with_google.md`.
- **Results vary by platform and by run.** The prompts, the gates and the report are the same everywhere, but each platform runs a different model, and ChatGPT cannot isolate the verifier from the reviewers. Expect the major findings to recur and the minor ones to vary.
- **A review can be wrong.** The gates enforce process, not truth. Treat "Must fix" as "check this first".
- **Cost.** A review of a 15-page document at `mid` depth uses roughly ten agent runs.
- **Tested:** the HTML renderer on two PDFs and a text file; the full pipeline run by hand in Claude Code on two documents; `deep_review.py` against a stub server only.
- **Not yet tested:** the rewrite skill, the Copilot files, the ChatGPT instructions, installing the plugin through the Claude Code plugin command, and `deep_review.py` against a live API.
- The report loads the Google Sans Flex font from Google Fonts; offline it falls back to the system font.

## Sources

- Jayaram et al., "Towards Automating Scientific Review with Google's Paper Assistant Tool", arXiv 2606.28277, and the public Deep Review FAQ and API schema: the staged architecture and output shape.
- Weng et al., "DeepReviewer 2.0: A Traceable Agentic System for Auditable Scientific Peer Review" (code: ResearAI/DeepReviewer-v2, MIT): the claim ledger, admission gate, named factual checks, verification category and opponent reading.

All prompt text in this repository is original.
