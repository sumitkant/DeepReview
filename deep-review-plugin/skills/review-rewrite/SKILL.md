---
name: review-rewrite
description: Rewrite a document from a deep review after the author has confirmed it. Applies only the comments the author accepted (from review_decisions.json exported by the review HTML page, or stated in chat), honours their notes, never invents facts, and returns the revised document with a change log and a list of facts still needed. Use when the user says to apply the review, rewrite, revise or fix the document based on the review.
---

# Review rewrite

`ROOT` is the plugin root (`${CLAUDE_PLUGIN_ROOT}` when set, otherwise two levels above this file). Read `ROOT/prompts/5_rewriter.md` and follow it exactly.

1. **Find the inputs.** The original document, and `review_decisions.json` (exported from `review.html`; look in the review folder and the user's Downloads folder, and ask for its path if it is not found). If the user gave decisions in chat instead ("apply all major ones except C5"), build the same JSON from `4_review.json` and their words, show them the list of comments you will apply, and wait for a yes.
2. **Do not start without decisions.** If nothing has been accepted, say so and point the user to the review page.
3. **Find the source.** Ask whether an editable source exists (Markdown, LaTeX, Word, HTML). Edit that if it does. If the only input is a PDF, write Markdown that follows the original's structure.
4. **Rewrite** per `5_rewriter.md`. Save the result next to the review as `<name>_revised.<ext>`; never overwrite the original.
5. **Check your work in code.** For each accepted comment with a quote, confirm the quoted text no longer appears unchanged in the revised document, or that you listed it under "Not applied" with a reason. Confirm every `[placeholder]` in the output is in the "Needs your input" list.
6. **Report.** Give the path of the revised file, the change log table, "Needs your input", and "Not applied". Offer to run `deep-review` again on the revised document.
