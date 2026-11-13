# Stage 0: Claim–evidence ledger

You read the whole document once, before any reviewing, and write down what it claims and what holds each claim up. You do not judge yet. Reviewers will use this ledger to decide where to push hardest.

## Input
- REVIEW PROFILE, AUTHOR CONTEXT (optional).
- DOCUMENT: full text.

## Task
1. State the document's thesis in one sentence: what the reader is meant to believe or do after reading it.
2. List the 3 to 7 core claims that carry the thesis. Take them from the document's own words (title, summary, introduction, conclusion, headline numbers). Do not invent claims and do not list minor details. A result with no idea behind it ("faster", "more") is not a claim by itself; pair it with what is said to cause it.
3. For each claim record:
   - `claim`: the claim in the author's terms, with the exact quote where it is stated most strongly.
   - `evidence`: where in the document the support is (page or section, and the quoted number, table, example or argument). Write `none found` if there is none.
   - `warrant`: the inference that gets from that evidence to the claim, in one sentence ("a 1.43x gain against an 8x ceiling shows the loop is memory bound").
   - `evidence_level`: `asserted` (stated, no support), `described` (an example, a single observation, a trend), `measured` (a controlled measurement or a derivation), `isolated` (measured with the alternative causes ruled out).
   - `claim_level`: how strong the wording is: `suggests`, `shows`, `proves or causes`, `always or universal`.
   - `depends_on`: ids of other claims this one needs.
4. Edge-removal test. For each claim ask: if this evidence or this warrant were wrong, would the thesis still stand? List as `load_bearing` the claims whose failure would collapse the thesis or a headline number.
5. List `mismatches`: every claim whose `claim_level` is stronger than its `evidence_level` supports.

## Output
Return only JSON:

```json
{
  "thesis": "string",
  "claims": [
    {
      "id": "K1",
      "claim": "string",
      "quote": "exact words from the document",
      "page": 1,
      "evidence": "string",
      "warrant": "string",
      "evidence_level": "asserted|described|measured|isolated",
      "claim_level": "suggests|shows|proves or causes|always or universal",
      "depends_on": []
    }
  ],
  "load_bearing": ["K1"],
  "mismatches": [{"id": "K1", "why": "string"}]
}
```
