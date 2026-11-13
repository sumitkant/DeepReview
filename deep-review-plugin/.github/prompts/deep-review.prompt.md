---
description: Deep multi-stage review of a document with verified, quote-anchored comments and an HTML report
agent: agent
---

Follow the instructions in [SKILL.md](../../skills/deep-review/SKILL.md) exactly. `ROOT` is the folder that contains `prompts/`, `profiles/` and `scripts/` (the folder two levels above this prompt file).

Document: ${input:document:path to the document}
Author context (optional): ${input:context:what the document is for, or leave empty}
Depth: ${input:depth:low, mid, high or extra_high}

Where the skill says "subagent", use `#runSubagent` with only the file paths and the segment as its brief. If subagents are not available in this session, do the reviewer passes one segment at a time, then start a NEW chat for the verifier step with only the files named in the skill, so that the verifier does not see the reviewers' reasoning. Use the terminal for every step the skill says to do "in code".
