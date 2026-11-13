---
name: deep-review
description: Reviews dense documents in stages (segment, parallel review, quote check, verify, synthesize), renders an annotated HTML report, and rewrites from the author's decisions.
---

You run three procedures, each defined in a skill file in this workspace. Read the file and follow it exactly; do not work from memory of it.

- Review a document: `skills/deep-review/SKILL.md`
- Produce the annotated HTML: `skills/review-html/SKILL.md`
- Rewrite after the author has decided: `skills/review-rewrite/SKILL.md`

`ROOT` in those files is the folder that contains `prompts/`, `profiles/` and `scripts/`.

Rules in every procedure: every comment quotes the document exactly and the quote is checked in the terminal; the verifier works from the document and the gathered evidence, not from the reviewers' reasoning; outside facts need a URL from a search made in this session or must be marked unverified; suggested edits and rewrites never add facts, they use `[placeholders]`; no scores; the HTML comes only from `scripts/render_review.py`.
