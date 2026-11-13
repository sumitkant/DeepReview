# deep-review plugin

Three skills that share one set of prompts and one renderer:

| Skill | What it does | Output |
|---|---|---|
| `deep-review` | Claim ledger, segment, review in parallel, gates in code, ground, verify, synthesize | `4_review.json`, `review.md`, then calls `review-html` |
| `review-html` | Annotated report: the document with each comment's passage highlighted beside the comment cards | `review.html` (one self-contained file) |
| `review-rewrite` | Rewrites the document from the comments the author accepted | `<name>_revised.<ext>`, change log, list of facts still needed |

The flow is: review, open `review.html`, mark each comment Accept or Dismiss and add notes, press "Export decisions" (saves `review_decisions.json`), then run the rewrite.

```
prompts/    0_ledger  1_segmenter  2_reviewer  3_verifier  4_synthesizer  5_rewriter
profiles/   resume  research-paper  technical-blog
scripts/    render_review.py   apply_gates.py   deep_review.py   extract_google_review.py
skills/     deep-review  review-html  review-rewrite          (Claude Code)
.github/    prompts/*.prompt.md  agents/deep-review.agent.md  (GitHub Copilot)
chatgpt/    custom-gpt-instructions.md                        (ChatGPT)
```

## Install

**Claude Code**

```
/plugin marketplace add D:\MyWorks\GenAI\DeepReview\deep-review-plugin
```
```
/plugin install deep-review@deep-review-local
```

Then ask: "deep review review2/my-post.pdf". Without the plugin system, copy the three folders under `skills/` into `~/.claude/skills/` and copy `prompts/`, `profiles/` and `scripts/` beside them.

**GitHub Copilot (VS Code)**: open this folder as the workspace, or copy `.github/`, `skills/`, `prompts/`, `profiles/` and `scripts/` into your own workspace. In agent mode run `/deep-review`, `/review-html`, `/review-rewrite`, or pick the `deep-review` agent. The prompt files point at the same `SKILL.md` files Claude uses.

**ChatGPT**: follow `chatgpt/custom-gpt-instructions.md`.

**Any OpenAI-compatible API, no agent**:

```bash
python scripts/deep_review.py doc.pdf --profile profiles/technical-blog.md --depth mid --out review_doc
```

It writes `4_review.json`, `review.md` and `review.html`. It does not search the web; pass evidence with `--search evidence.md`.

The HTML step needs PyMuPDF for PDF input: `pip install pymupdf`. Text and Markdown input needs nothing.

## Will every platform give the same results?

The same prompts, the same JSON shapes and the same renderer run everywhere, so the report format and the rewrite rules are identical. The findings will not be identical, for three reasons:

1. **Different models.** Each platform runs its own model; a review is model judgement.
2. **Isolation.** Claude Code and the script run reviewers and the verifier in separate contexts. Copilot does where subagents are available. ChatGPT cannot, so its verifier is less independent.
3. **Run-to-run variation.** Two runs on the same platform also differ.

Expect the same major issues to recur across platforms and the minor ones to vary.

## How close is it to Google's Deep Review?

Google's prompts are not public; these are written from Google's paper, FAQ and API schema, and adjusted after comparing against two real Deep Review outputs. On a blind test (a 15-page blog post reviewed before Google's review was seen), of Google's 28 comments the kit found 13, found 10 in part and missed 5, and it raised about a dozen points Google did not. Details: `deep-review-kit/output/blog/comparison_with_google.md`.

One deliberate difference: Google's suggested fixes sometimes contain invented specifics. These prompts require `[placeholders]` for any fact the document does not contain, in the review and in the rewrite.

## What the review checks, and how the report groups it

- **Claim ledger first.** Before reviewing, the document's thesis and core claims are written down with the evidence and inference behind each; claims whose failure would collapse the thesis are marked load-bearing and get the most scrutiny.
- **Opponent reading.** Reviewers assume the document is wrong and look for the simpler alternative explanation.
- **Six named factual checks** (numbers, text against tables and code, setup consistency, measure against claim, cause, outside facts) before anything is rated major.
- **Admission gate, enforced in code.** Nothing is rated critical or major without an exact quote, a named check with its outcome, and a stated impact. Findings that fail are kept as "Needs verification" and capped at minor.
- **Extraction artifacts** (split words, line-end hyphens, reordered lines, lost icons) are never findings.

The HTML report opens with five counts, each in its own colour and each a filter: Findings; Must fix (critical and major); Minor (typos and small issues); Can ignore (optional suggestions); Needs verification (not confirmed). The page uses the Google Sans Flex font, loaded from Google Fonts, so it needs an internet connection to show that font; offline it falls back to the system font.

## What has been tested

- The ledger stage, admission gate and "Needs verification" type have been run once on each test document, by hand in Claude Code following the skill's stages (`deep-review-kit/output/blog_v2`; the second test document is private and not in the repository). `apply_gates.py` was run on both.
- `render_review.py`: run on two PDFs (2 and 15 pages) and a text file; all comments located; highlight-to-card linking, Accept / Dismiss and the progress counter and the "Export decisions" JSON checked in a browser.
- `deep-review` procedure: run twice in Claude Code by hand, following the same stages the skill describes. The packaged skill has not been installed and invoked as a plugin.
- `deep_review.py`: control flow, including the HTML step, tested against a stub model server; not run against a live API.
- `review-rewrite`, the Copilot files and the ChatGPT instructions: written, not run.
