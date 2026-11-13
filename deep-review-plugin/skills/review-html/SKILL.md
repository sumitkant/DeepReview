---
name: review-html
description: Turn a deep-review result (4_review.json) into one HTML page that opens with a colour-coded summary (findings, must fix, minor, can ignore, needs verification) and shows the document with each comment's passage highlighted in its severity colour beside the comment cards, with Accept / Dismiss per comment and an export of the author's decisions. Use after a deep review, or when the user asks for the annotated, highlighted or HTML version of a review.
---

# Review HTML

`ROOT` is the plugin root (`${CLAUDE_PLUGIN_ROOT}` when set, otherwise two levels above this file).

Inputs: the reviewed document (`.pdf`, `.txt` or `.md`) and the review JSON. The JSON must have this shape; if you are given a review in another form (Markdown, a chat transcript), first convert it to this shape without changing its content:

```json
{
  "review_markdown": "### Summary ... ### Strengths ... ### Weaknesses ...",
  "anchored_comments": [
    {
      "comment_id": "C1",
      "severity": "CRITICAL|MAJOR|MINOR|SUGGESTION",
      "needs_verification": false,
      "summary": "short title",
      "body_markdown": "the comment",
      "suggested_edit": "drop-in replacement text, or empty",
      "location": {"page": 3, "quote": {"exact": "words copied from the document"}},
      "grounding_urls": ["https://..."]
    }
  ]
}
```

Steps:

1. For a PDF, make sure PyMuPDF is importable (`python -c "import pymupdf"`). If it is not, ask before installing it with `pip install pymupdf`.
2. Run:

   ```bash
   python "ROOT/scripts/render_review.py" "<document>" "<review folder>/4_review.json" "<review folder>/review.html"
   ```

3. Read the script's last line. It reports how many comments were located in the document. For each comment listed as "not located", compare its `quote.exact` with the document text: fix the quote so it matches the document character for character (do not change the comment), then run the script again. A quote that spans a page break or sits inside a figure may not be locatable; say so.
4. Report the summary line the script prints: findings, must fix, minor, can ignore, needs verification. The page shows the same five numbers as coloured tiles at the top, and each tile filters the page to that category. The categories are fixed by the script: Must fix = CRITICAL and MAJOR; Minor = MINOR (typos and small issues); Can ignore = SUGGESTION; Needs verification = any comment with `needs_verification` true, whatever its severity.
5. Tell the user the path of `review.html` and how to use it: click a highlight or a card to jump between them, mark each comment Accept or Dismiss, add notes, then press "Export decisions" to save `review_decisions.json` for the `review-rewrite` skill.

Do not hand-write the HTML. The script is the single source of the page so that every platform produces the same output. Do not edit comment text while rendering.
