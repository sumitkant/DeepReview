---
description: Render a deep-review result as an annotated HTML page with highlights
agent: agent
---

Follow the instructions in [SKILL.md](../../skills/review-html/SKILL.md) exactly. `ROOT` is the folder that contains `prompts/`, `profiles/` and `scripts/` (the folder two levels above this prompt file).

Document: ${input:document:path to the reviewed document}
Review JSON: ${input:review:path to 4_review.json}

Where the skill says "subagent", use `#runSubagent` with only the file paths and the segment as its brief. If subagents are not available in this session, do the reviewer passes one segment at a time, then start a NEW chat for the verifier step with only the files named in the skill, so that the verifier does not see the reviewers' reasoning. Use the terminal for every step the skill says to do "in code".
