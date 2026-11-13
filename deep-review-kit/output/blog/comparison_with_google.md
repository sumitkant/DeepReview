# Blind test: Google Deep Review vs. the kit on the blog post

The kit's review (`review.md`, `4_review.json`) was produced before Google's `review2.html` was added. The two reviews are kept separate: nothing from Google's output was merged into the kit's.

| | Google | Kit |
|---|---|---|
| Comments | 28 | 39 |
| Critical / major / minor / suggestion | 0 / 6 / 18 / 4 | 0 / 12 / 20 / 7 |
| Overall feedback | not present in the saved page | Summary, 4 strengths, 5 weaknesses |

## Google's 28 comments against the kit

| # | Google comment (severity, page) | Kit |
|---|---|---|
| G1 | Missing "the" before "same compute budget" (minor, 1) | Found (C3) |
| G2 | Typo "modfications", "how GPU works" (minor, 1) | Found (C3) |
| G3 | Missing full stop, TL;DR paragraph 3 (minor, 1) | Found (C3) |
| G4 | Page-2 one-liner says only matmuls are downcast (minor, 2) | Found (C13, same quote) |
| G5 | "ahead of time" vs just-in-time compilation (minor, 2) | Found (C18) |
| G6 | Missing full stop on chart caption (minor, 2) | Part: C3 groups punctuation slips, this one not listed |
| G7 | Batch size, sequence length, optimizer missing (major, 3) | Found (C6, major) |
| G8 | RTX 5070 8 GB is the laptop GPU (minor, 3) | Found (C5, rated major) |
| G9 | Space before full stop, bullet punctuation (minor, 3) | Missed |
| G10 | Timing harness: transfers inside timer, no pre-timer sync, warm-up, clock (major, 3) | Part: C34 has `.to(device)` in the timed region and `perf_counter`; pre-timer sync and warm-up missed |
| G11 | Punctuation around "i.e." (minor, 3) | Found (C3, C7) |
| G12 | On CUDA, 'high' and 'medium' both mean TF32 (minor, 4) | Part: C11 flags the same comment line as loose, without this claim |
| G13 | 8x A100 ceiling does not apply to an RTX 5070 (major, 4) | Part: C9 says the same (minor) without Google's consumer-GPU throughput figures |
| G14 | "1.5-3x" vs measured 1.43x (suggestion, 5) | Found (C12) |
| G15 | Autocast: weights are cast on the fly; why backward is outside (major, 6) | Part: C13 covers what autocast converts; backward-pass point missed |
| G16 | PyTorch does document autocast ops (minor, 6) | Found (C13) |
| G17 | Diagram truncates 0.044715 and omits steps (minor, 8) | Part: C17 covers the GELU op count and diagram, not the truncation |
| G18 | HBM vs GDDR7 (minor, 8) | Found (C19, rated major) |
| G19 | `optimizer.step()` stays unfused; fused AdamW (suggestion, 8) | Missed |
| G20 | Attention: per-line accounting, compile already active, logits larger (minor, 10) | Part: C22 has "logits are about 4x larger"; C17 touches compile interaction; per-line accounting missed |
| G21 | "10% faster" vs 1.12x (minor, 10) | Found (C25) |
| G22 | Suggest fused linear cross-entropy kernels (suggestion, 11) | Missed |
| G23 | `block_size` 4096 vs T = 1024 (major, 12) | Found (C30, major); Google adds the positional-embedding mismatch on `from_pretrained` |
| G24 | Table vs waterfall chart labels (suggestion, 13) | Part: C4 and C28 cover label and format inconsistency generally |
| G25 | Additive millisecond split is order dependent (minor, 14) | Part: C37 and C8 raise it differently |
| G26 | A100 comparison not normalised for tokens per step (major, 14) | Found (C36, rated minor after verification) |
| G27 | Pre-Ampere advice should use float16 autocast (minor, 14) | Missed as a recommendation; C38 only notes the conclusion's gaps |
| G28 | Replicates an existing curriculum; add systems citations (minor, 15) | Missed |

Count: 13 found, 10 found in part, 5 missed. On the resume, before retuning, it was 15 found, 4 in part, 5 missed out of 24. The retuned prompts closed the copy-editing gap (typos, punctuation, "ahead of time", percent conventions); what remains is depth on a few mechanisms and a kind of comment the kit does not produce.

## What the kit raised that Google did not

- The "memory bound" diagnosis is not isolated: Amdahl's law fits the same 1.43x (C8), and the autocast result contradicts it (C15). Google accepts the diagnosis as broadly valid.
- "Karpathy saw about 30%" from vocabulary padding; his own timings show 96 to 93 ms (C31).
- Karpathy's script has compile off for the whole run (C21).
- No evidence the flash kernel ran on this Windows build (C23).
- Quality claims ("no accuracy we can measure", "loss curve unchanged") with no measurement (C35).
- All timings are multiples of 5 ms, so the last two gains sit at the reporting resolution (C34).
- Weight tying ignored in the "two largest matrices" claim (C27); head count is not a matmul dimension (C32); the tile mechanism is asserted (C26); the "about 60%" figure is unsourced (C10).
- Conclusions omit optimization 5 (C38); "largest single gain" is true by ratio only (C20); glossary and identifier inconsistencies (C29, C33).

## What this shows about the pipeline

1. **Coverage of checkable facts is close.** Both found the missing setup, the 8 GB card, HBM, `block_size`, the autocast documentation claim, the 1.5-3x range, the A100 comparison and the percent wording.
2. **Google adds forward-looking suggestions the kit does not make.** G19, G22 and G28 propose related techniques (fused AdamW, fused cross-entropy) and foundational citations. The kit's reviewer was only asked to find problems. Added to the reviewer prompt after this test.
3. **Google goes one level deeper on mechanism in places**: G10 (pre-timer sync, warm-up), G15 (weights cast on the fly, autograd replaying dtypes), G20 (which lines materialise the matrix). The kit's second pass spent its depth on causal reasoning instead.
4. **Google files copy-edits one per slip, each with a drop-in fix.** The kit grouped them into one comment. One per slip is more useful for an automatic rewrite. Changed in the reviewer prompt.
5. **The comment label is not universal.** On the resume, Google opened bodies with "Potential Concern (...)" or "Definitive Flaw"; on the blog it mostly does not. The kit's prompt had made the label mandatory, which over-fitted to one sample. Now optional.
6. **Severity:** Google rated naming errors (HBM, 8 GB) minor and method or reproducibility problems major. The kit rated HBM and 8 GB major. Neither produced a critical.

## Claims in Google's review that were not verified here

These are specific and may be right, but nothing gathered for this test confirms them, and the kit's verifier would have marked them unverified:

- G12: that on CUDA `'medium'` is identical to `'high'` (TF32). The general PyTorch page says `'medium'` uses bfloat16 internally where a fast algorithm exists.
- G13: about 30.9 TFLOPS and a 1:1 TF32-to-FP32 ratio on the RTX 5070.
- G25 and G27: that PyTorch's flash kernel requires 16-bit inputs.
- G19: that Karpathy's 93 ms figure includes `fused=True` AdamW. The chapter list puts 93 ms at the vocabulary change.

Check these before acting on them.
