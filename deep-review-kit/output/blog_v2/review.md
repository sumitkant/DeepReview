### Summary

This is a tutorial blog post in a "Transformers from scratch" series. It applies five small code changes to the training loop of a GPT-2 124M model on Tiny Shakespeare: TF32 matmul precision, bfloat16 autocast, `torch.compile`, flash attention through `F.scaled_dot_product_attention`, and padding the vocabulary from 50,257 to 50,304. It reports the time per training step after each change on one RTX 5070 under Windows: 250, 175, 165, 95, 85 and 80 ms, about 3× overall. Each section gives the one-line change, a measured before and after, a mechanism for the gain, "use it when" and "limitations" lists and a glossary. The post reads the sequence of gains as evidence that the loop is memory bound, compares its results with Andrej Karpathy's A100 run, and closes with two decision rules for the reader.

### Strengths

- **One change at a time, with numbers that reconcile:** The ladder on page 2, the per-section "MEASURED" boxes and the results table on page 13 agree with each other, and the ratios check (250/175 = 1.43, 165/95 = 1.74, 250/80 = 3.13; the savings sum to 170 ms). A reader can follow exactly which line produced which figure.
- **GPU timing done with a synchronisation point:** The timing listing on page 3 calls `torch.cuda.synchronize()` before reading the clock, and page 8 tells the reader to exclude the first, compiling step. These are the two mistakes most often made when timing GPU code, and the post avoids both in what it shows.
- **Limitations stated beside each change:** Every section lists where the change does not apply, for example that `from_pretrained` needs a 50,257 vocabulary, that `torch.compile` recompiles when input shapes change and needs `triton-windows` on Windows, and that flash attention hides the attention weights. This is practical information for someone copying the code.
- **Clear account of bfloat16 against float16:** Page 5 explains the range and precision trade-off and why float16 needs a `GradScaler` while bfloat16 does not, and page 6 shows which tensors change dtype inside the autocast block. This matches the PyTorch Automatic Mixed Precision documentation.

### Weaknesses

- **The memory-bound diagnosis is not isolated from simpler explanations:** Page 4 concludes from `1.43×, not 8×` that `the loop is memory bound`, and page 14 says `That one number predicts the rest.` The 8× figure is the A100 datasheet ratio of peak TF32 to peak FP32 throughput (156 against 19.5 TFLOPS, NVIDIA A100 datasheet), not a figure for the RTX 5070, and a 1.43× step gain is what Amdahl's law gives when matrix multiplies are only part of the step time, with no memory limit involved. The post's own next result goes against the forecast: page 6 reports `Only 6%` from halving the activation width, after which the bottleneck is redescribed as the number of round trips, so "memory bound" carries two meanings (bytes moved on pages 3 to 5, number of trips on pages 6 and 14). The author might consider presenting the diagnosis as a hypothesis that fits the sequence, and adding a profiler breakdown of one step, or the same ladder in a different order, if the stronger wording is to stay.
- **No accuracy data behind the claim that the speedups are free:** The TL;DR promises `on-par performance`, page 4 says TF32 `costs no accuracy we can measure`, page 10 says `the loss curve is unchanged apart from floating-point noise`, and conclusion 01 repeats the claim. No loss value, loss curve or validation result appears anywhere in the post, and page 6 says autocast is `Less precise than float32` and may need the reader to `train a little longer`. Since "train 3× faster" depends on quality being preserved, please consider reporting the training loss at a fixed step with and without each change, with the run-to-run spread, and softening `Always on those cards` to a default for this kind of workload.
- **The measurement protocol is not stated, and the smallest gains are at its resolution:** The setup on page 3 gives `Metric: wall-clock milliseconds per training step` but no batch size, sequence length, number of steps averaged, warm-up, spread or exact PyTorch version. Every reported time is a multiple of 5 ms and the baseline is written `~250 ms`, so the 85 → 80 ms vocabulary result (`runs 6% faster`, page 12) is one unit of resolution, and the two 10 ms steps are two. The title's `3x` for `Your LLM` therefore rests on one configuration on one card. The author might consider adding the configuration to the setup, reporting a mean or median with spread over a stated number of steps, and describing the vocabulary change as unmeasurable on this card if the difference falls inside that spread.
- **Causes are assigned to the autocast and `torch.compile` results without a measurement that separates them:** Page 8 says of the 165 → 95 ms gain `This is the cost autocast couldn't reach`, attributing it to kernel fusion and fewer memory round trips, but the same line also removes Python dispatch, and the two effects are not timed apart. Page 6 starts from `Halving the activations should have helped more`, while the same page says softmax, layer norm and the loss stay in float32 and the weights stay float32, so the data moved was not halved (the PyTorch AMP documentation lists these ops as autocasting to float32). Please consider stating that the 70 ms is the combined saving, or adding a profile of kernel counts and CPU-side time before and after compilation.
- **Hardware and configuration details do not match the setup described:** Page 8 explains fusion by `HBM, the GPU's main memory, holds tens of gigabytes`, while the setup lists `one RTX 5070 (8 GB)`; GeForce cards use GDDR memory, and published specifications give the desktop RTX 5070 12 GB of GDDR7, with 8 GB belonging to the RTX 5070 Laptop GPU (TechSpot and LaptopMedia specification pages). The config listing on page 12 has `block_size: int = 4096`, against `T = 1024` on page 10 and the GPT-2 124M model named in the setup. The same page says `Karpathy saw about 30%` from vocabulary padding, where the chapter list of the cited video gives 96 → 93 ms, about 3%. The author might consider naming the exact card and its memory, using "GPU memory (VRAM)" in the text and diagram, correcting the config listing to the values used for the timed runs, and citing or removing the 30% figure.

## Detailed feedback

### C1 · MINOR · page 1

**Title promises 3x for 'Your LLM' from one card, one model, one run**

> 5 Lines of Code to Make Your LLM

**Potential Concern (Scope of claim):** The title addresses the reader's model (`Your LLM`, `3x Faster`), while the subtitle is correctly scoped to what was measured (`made the smallest GPT-2 (124M parameter model) train 3x faster on a consumer-grade RTX 5070 GPU`). The evidence level is one measured run on one setup; the title's wording needs a result shown across setups.

The post itself supplies the counter-evidence: `about 11× against our 3.1×` on an A100 (page 14), `expect 1.5–3×` against a measured 1.43× (pages 4-5), and a vocabulary-padding gain that changed from about 30% to 6% with the PyTorch version (page 12). The 3x is also a ratio of time per step, not of time to reach a given loss; see the separate comment on quality.

**Suggested Improvement:** Scope the title to the measurement, as the subtitle already does, or say in the TL;DR that the multiplier depends on GPU, PyTorch version, batch size and sequence length and give the range seen (3.1× here, about 11× in Karpathy's A100 run).

**Suggested fix:** 5 Lines of Code That Made Our GPT-2

### C2 · MINOR · page 1

**Letter "x" in the title and TL;DR, "×" in the rest of the post**

> Train 3x Faster on GPU

**Definitive Flaw:** The speedup is written `3x` three times on page 1 and with the multiplication sign `×` everywhere else in the post (pages 4, 5, 8, 10, 13, 14).

**Suggested Improvement:** Use `×` throughout, including the title, subtitle and TL;DR.

**Suggested fix:** Train 3× Faster on GPU

### C3 · SUGGESTION · page 1

**Subtitle says "single-line exploits", TL;DR says "one-line changes"**

> 5 must-use single-line exploits that made the smallest GPT-2 (124M parameter model) train 3x faster on a consumer-grade RTX 5070 GPU.

**Potential Concern:** The subtitle and the TL;DR describe the same thing in different terms: `5 must-use single-line exploits` against `five one-line changes`. Pick one term ("one-line changes" is used most often) and spell out the number at the start of a sentence. The parenthesis is also misplaced: "the smallest GPT-2 (124M parameter model)" should attach "model" to GPT-2 and keep only the size in brackets.

**Suggested Improvement:** Align the subtitle with the TL;DR.

**Suggested fix:** Five must-use one-line changes that made the smallest GPT-2 model (124M parameters) train 3× faster on a consumer-grade RTX 5070 GPU.

### C4 · MINOR · page 1

**TL;DR second sentence: missing comma, missing article, doubled "with"**

> However we can use some tactics to achieve on-par performance with same compute budget with a few modifications.

**Definitive Flaw:** `However we can use some tactics to achieve on-par performance with same compute budget with a few modifications.` has three slips: a sentence-opening "However" needs a comma, "same compute budget" needs "the", and the two stacked "with" phrases read awkwardly.

**Suggested Improvement:** Recast as below.

**Suggested fix:** However, a few modifications let us achieve performance on par with the baseline on the same compute budget.

### C5 · MINOR · page 1

**Typo "modfications" in the TL;DR**

> These modfications and simple yet powerful exploits to fully utilize the capabilities of modern GPUs can significantly reduce training time.

**Definitive Flaw:** `modfications` is missing an "i". The subject "These modifications and simple yet powerful exploits to fully utilize ..." is also long before the verb arrives; the edit shortens it without changing the meaning.

**Suggested Improvement:** Correct the spelling and tighten the subject.

**Suggested fix:** These modifications are simple yet powerful exploits that fully utilize the capabilities of modern GPUs and can significantly reduce training time.

### C6 · MINOR · page 1

**Missing article in "how GPU works"**

> Most of it comes down to learning how GPU works.

**Definitive Flaw:** `how GPU works` needs an article (or a plural). The post uses "the GPU" and "GPUs" everywhere else.

**Suggested Improvement:** Add the article.

**Suggested fix:** Most of it comes down to learning how a GPU works.

### C7 · MINOR · page 1

**TL;DR headline sentence: capital "Model", missing hyphen, comma and full stop**

> We apply five one-line changes to a 124M parameter GPT-2 Model's training loop and reduce training time per step from 250 ms to 80 ms on a single RTX 5070 making training 3x faster

**Definitive Flaw:** Four slips in the highlighted summary sentence: "Model's" is capitalised mid-sentence (lower case everywhere else); the compound modifier "124M parameter" needs a hyphen (also in the subtitle); a comma is needed before the participle "making"; and the sentence has no full stop in the PDF.

**Suggested Improvement:** Use the corrected sentence below.

**Suggested fix:** We apply five one-line changes to a 124M-parameter GPT-2 model's training loop and reduce training time per step from 250 ms to 80 ms on a single RTX 5070, making training 3× faster.

### C8 · MINOR · page 1

**'Five one-line changes to the training loop' does not match the listings**

> We apply five one-line changes to a 124M parameter GPT-2 Model's

**Definitive Flaw:** The TL;DR says the five changes are one-line edits to the `training loop`. By the post's own listings, only the autocast `with` block is in the loop; the flash attention change replaces four lines in `CausalSelfAttention.forward`, the vocabulary change is in the config, and TF32 and `torch.compile` are setup lines. `Model's` is also capitalised here but lower case elsewhere.

**Suggested Improvement:** Describe them as five small changes to the training script.

**Suggested fix:** We apply five small changes, about one line each, to a 124M-parameter GPT-2 model's code, config and

### C9 · MINOR · page 1

**'Parameters and weights' listed as separate things; gradients omitted**

> The default state: activations, parameters and weights are all represented in float32.

**Definitive Flaw:** `parameters and weights` are the same thing in this context, and the matching sentence on page 3 lists `weights, activations, gradients` instead. Use one list in both places.

**Suggested Improvement:** Align with page 3.

**Suggested fix:** The default state: weights, activations and gradients are all represented in float32.

### C10 · MINOR · page 3

**ASCII arrow in prose and "triton" vs "triton-windows" in Setup**

> Windows needs triton -> pip install -U "triton-windows>=3.8,<3.9"

**Definitive Flaw:** `Windows needs triton -> pip install ...` uses an ASCII arrow as punctuation, where the rest of the post uses the typeset arrow "→" (measurement boxes and the results table). The package is called `triton-windows` on page 9 but `triton` here.

**Suggested Improvement:** Replace the arrow with a colon and name the package the same way in both places.

**Suggested fix:** Windows needs the triton-windows package: pip install -U "triton-windows>=3.8,<3.9"

### C11 · MAJOR · page 3

**Setup omits batch size, sequence length, run count, variance and PyTorch version**

> Metric: wall-clock milliseconds per training step

**Definitive Flaw (Reproducibility):** The Setup section gives model, data, hardware and metric, but not the settings that determine a per-step time.

- **Batch size and sequence length:** neither is stated. The only sequence lengths in the post are `At T = 1024` (page 10) and `block_size: int = 4096` (page 12), which do not agree with each other. Milliseconds per step is meaningless without B and T; tokens per second would be the comparable figure.
- **How many steps were timed:** the listing under `timing one step honestly` measures one step. The post does not say whether 250 ms is one step, a mean or a median, how many steps were discarded as warm-up, or what the spread was. The later differences of 10 ms and 5 ms need that spread to be credible.
- **Software version:** `PyTorch 2.x` covers several years of releases, and page 12 states that the size of one of the five gains changed between versions. The author pins `triton-windows>=3.8,<3.9`, so the environment was evidently fixed and the exact PyTorch version can be stated. CUDA version, driver and Python version are also absent.
- **Approximate baseline:** `~250 ms` on page 3 becomes an exact `250 ms` in the TL;DR, the table and the 3.13× ratio.

A strict reader will treat the six step times as a single unreplicated run of an unknown configuration.

**Suggested Improvement:** Add batch size, sequence length, optimizer, exact PyTorch/CUDA/driver versions, and the timing protocol (for example: median of N steps after discarding the first M, with min and max) to the Setup list, and report tokens per second alongside ms per step.

**Suggested fix:** Metric: wall-clock milliseconds per training step at batch size [B] and sequence length [T], [median/mean] of [N] steps after [M] warm-up steps (spread ±[x] ms); PyTorch [exact version], CUDA [version]

### C12 · MINOR · needs verification · page 3

**Timing listing: time.time(), host-to-GPU copy in timed region, single step**

> logits, loss = model(x.to(device), y.to(device))

**Potential Concern (Measurement method):** The listing is titled `timing one step honestly` and correctly calls `torch.cuda.synchronize()` before reading the clock. Three details weaken it:

- **Clock:** `time.time()` is a wall clock that can be adjusted and, on some Windows and Python combinations, has coarse resolution. `time.perf_counter()` is the standard choice for interval timing. This matters here because two of the five reported gains are 5 ms and 10 ms.
- **Work inside the timed region:** `x.to(device)` and `y.to(device)` copy the batch from host memory inside the measurement. For token indices the cost is likely small, but it is a fixed term that the five changes cannot reduce, and it is not part of what the post later attributes the time to.
- **Listing mismatch:** the TL;DR baseline is `logits, loss = model(x, y)`; here it is `model(x.to(device), y.to(device))`.

The listing also times one step and has no warm-up; page 8 later says to `start timing from the second step` for the compiled model only.

**Suggested Improvement:** Use `time.perf_counter()`, move the batch to the device before `t0`, time a run of steps after warm-up and report the median, and make the TL;DR baseline line match.

**To verify:** the Python version used and its release notes for the resolution of time.time() on Windows; rerunning the ladder with time.perf_counter() and the batch moved to the device before t0 would show whether the figures change.

### C13 · MINOR · page 3

**Mismatched punctuation around the "i.e." aside in the baseline box**

> Every tensor in this loop i.e. weights, activations, gradients — is float32.

**Definitive Flaw:** The parenthetical list opens with a bare "i.e." and closes with an em dash. An aside needs the same mark on both sides. "i.e." is also unnecessary once the dashes are there.

**Suggested Improvement:** Use a matching pair of dashes.

**Suggested fix:** Every tensor in this loop — weights, activations, gradients — is float32.

### C14 · MINOR · page 3

**Baseline paragraph: 'every tensor is float32' and 'far more precision than training needs'**

> Every tensor in this loop i.e. weights, activations, gradients — is float32.

**Potential Concern:** Three points in this paragraph:

- **Scope:** `Every tensor in this loop` excludes the integer token tensors `x` and `y`; 'every floating-point tensor' is what is meant.
- **Unsupported generalisation:** `far more precision than training needs` is asserted. Pages 5 and 6 keep the weights, softmax, layer norm and loss in float32 because lower precision there causes problems, so the accurate statement is that many operations tolerate less precision.
- **Punctuation:** `i.e.` opens the aside and an em dash closes it (confirmed in the PDF); the pair should match. `memory bus` is also not the term used later (`GPU memory`, `HBM`).

**Suggested Improvement:** Narrow the claim and fix the punctuation.

**Suggested fix:** Every floating-point tensor in this loop (weights, activations, gradients) is float32.

### C15 · MAJOR · page 4

**1.43x from TF32 fits Amdahl's law without any memory limit**

> So the cores spend their time waiting for data, not doing arithmetic: the loop is memory bound.

**Definitive Flaw (Causal inference):** From `1.43×, not 8×` the post concludes `So the cores spend their time waiting for data, not doing arithmetic: the loop is memory bound.` The conclusion does not follow from the number.

- **Amdahl's law gives the same number.** TF32 only touches matmuls (the post's own limitation: `Matmuls only. Layer norms, softmax, GELU and the optimizer are untouched`). A 30% saving is what a full 8x on about 34% of the step produces: 0.343 × (1 − 1/8) = 0.30. Under that reading about 164 of the remaining 175 ms is non-matmul work (element-wise operations, normalisation, the loss, the optimizer, Python dispatch, kernel launches), which is also what the later 70 ms compile gain suggests. No idle tensor cores are needed to explain it.
- **Tension with the section lead.** `Most of a training step is matrix multiplication` and `in GPT-2 they are most of the work` are assertions about operation counts, not measured shares of wall time. If matmuls were most of the time, the measured saving implies they sped up by about 2x or less, which then needs its own explanation; the post gives no measurement to choose between the two readings.
- **The ceiling is from another card.** 19.5 and 156 TFLOPS are A100 datasheet peaks, the second for tensor cores and the first for ordinary float32 units. The ratio on an RTX 5070 is not given, so the '8×' the result is measured against is not established for the test hardware.
- **Unsourced figure.** `rarely keeps the tensor cores busy more than about 60% of the time` has no reference and no measurement on this card.
- **Own range missed.** `expect 1.5–3× on a real training loop` sits beside a measured 1.43×.
- **What is in the timed region.** The step timed on page 3 includes the optimizer update, gradient zeroing and the host-to-device copy of the batch, none of which TF32 touches; they dilute the ratio further.

**Suggested Improvement:** Present 'memory bound' as one hypothesis. To support it, show a per-operation profile of the baseline step (share of time in matmul kernels against everything else) and the time of an isolated large matmul with TF32 off and on for this card. If the matmul alone speeds up several-fold while the step gains 1.43x, the limit is the non-matmul share, not memory. Change the expected range to include the post's own result.

Also at page 4: "156 for TF32, an 8× ceiling.".

Sources: https://images.nvidia.com/data-center/a100/a100-datasheet.pdf

**Suggested fix:** The step as a whole gained far less than the multiply did. One number cannot say why: either matrix multiplies are a smaller share of the step time than their share of the arithmetic suggests, or they are held back by data movement.

### C16 · MINOR · needs verification · page 4

**Unsourced 60% tensor-core utilisation figure**

> tuned training code rarely keeps the tensor cores busy more than about 60% of

**Potential Concern (Unsourced figure):** `Even well-tuned training code rarely keeps the tensor cores busy more than about 60% of the time.` This is a specific number stated as general fact. It has no citation, and the post reports no utilisation measurement of its own. If it comes from Karpathy's video, it should be attributed there and described as his remark, not as an established figure.

**Suggested Improvement:** Attribute the figure to its source, or replace it with the utilisation measured on this run.

**To verify:** the TF32 section of the cited video, to see whether the 60% figure is Karpathy's remark.

**Suggested fix:** tuned training code, [source] notes, rarely keeps the tensor cores busy more than about 60% of

### C17 · MAJOR · page 4

**No-accuracy-cost claims have no loss data and conflict with page 6**

> Always on those cards. It is one line and costs no accuracy we can measure.

**Definitive Flaw (Unsubstantiated claim):** The segment makes three accuracy statements and shows data for none of them:

- `It is one line and costs no accuracy we can measure.` (page 4)
- `The results are slightly less exact, but the training loss looks no different.` (page 4)
- `Precision is now as low as it can safely go.` (page 7)

"We can measure" implies a measurement was made, yet the post reports only milliseconds per step. The autocast limitations then say `Less precise than float32. We accept that for the speed and, if needed, train a little longer.` That is a concession that lower precision may cost steps, which is a cost in exactly the quantity the post is optimising (time to train), and it contradicts the page 14 conclusion that the two precision changes together `cost no accuracy we can measure`.

`Always on those cards` is universal advice. TF32 and bfloat16 are widely used for transformer training, so the advice is reasonable in spirit, but the post's evidence is one unreported run on Tiny Shakespeare; workloads that are sensitive to matmul precision exist, which is why PyTorch leaves TF32 for matmul off by default.

**Suggested Improvement:** Add the evidence: training (and ideally validation) loss at a fixed step count for baseline, TF32 and TF32 + autocast with the same seed, or overlaid loss curves. Then scope the advice to what was tested and reconcile the page 6 limitation with the page 4 and page 14 wording.

Also at page 14: "autocast. Together they are two lines and cost no accuracy we can"; page 14: "Together they are two lines and cost no accuracy we can measure."; page 1: "use some tactics to achieve on-par performance with same compute budget"; page 10: "the loss curve is unchanged apart from floating-point noise".

**Suggested fix:** A sensible default on those cards for transformer training. It is one line, and in our run the training loss after [N] steps was [value] against [value] for float32.

### C18 · MINOR · page 5

**TF32 "expect 1.5–3×" vs the post's measured 1.43×**

> Capped by memory bandwidth, so expect 1.5–3× on a real training loop, not

**Definitive Flaw (Number against own measurement):** The TF32 section reports `250 → 175 ms`, which is 250 / 175 = 1.43×, then advises `expect 1.5–3× on a real training loop, not 8×`. The post's own result is below that range, and no source or second measurement supports 1.5 to 3×.

**Suggested Improvement:** State the expectation from what was measured, or cite where the 1.5 to 3× range comes from and say why this run falls below it.

**Suggested fix:** Capped by memory bandwidth, so expect far less than the datasheet ratio on a real training loop (1.43× here), not

### C19 · MINOR · needs verification · page 6

**Autocast listing passes undefined device as device_type**

> with torch.autocast(device_type=device, dtype=torch.bfloat16):

**Potential Concern (Code reproducibility):** The same variable is used for `.to(device)` and for `device_type=device`. The two arguments accept different things: `device_type` wants the device type as a plain string. Since the post never shows how `device` is set, the listing is not safe to copy as shown. The identical line appears in the TL;DR on page 2.

**Suggested Improvement:** Pass the type explicitly, or show the definition of `device` in the setup. Apply the same change to the page 2 listing.

Sources: https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py

**To verify:** run the line with device = 'cuda:0' (or a torch.device object) and see whether torch.autocast accepts it.

**Suggested fix:** with torch.autocast(device_type="cuda", dtype=torch.bfloat16):

### C20 · MAJOR · page 6

**Autocast premise 'activations halved' contradicted by the post's own op list**

> Halving the activations should have helped more, but by now a

**Potential Concern (Causal attribution):** The box reads `Only 6%. Halving the activations should have helped more, but by now a different cost dominates.` The conclusion that a different cost dominates depends on the bytes really having been halved.

- **The post's own description says otherwise.** A few lines above: `Softmax, layer norm and the loss stay in float32`, and `The weights stay float32`. In a GPT-2 block every sub-layer is preceded by a layer norm, so the tensors entering each attention and MLP sub-layer are float32 by that description, and the float32 weights must be converted for each 16-bit matmul. The largest tensor in the step, the logits, is 16-bit only until the loss, which the post says runs in float32. The lead on page 5, `The forward pass stores activations in 16 bits instead of 32`, overstates what the op-by-op account on page 6 allows.
- **Residual stream (to confirm).** Under PyTorch's type promotion, adding a 16-bit sub-layer output to a float32 residual gives float32, in which case the residual stream stays float32 throughout. This is worth checking in the notebook by printing the dtype of the block input and output inside the autocast region.
- **Simpler reading of the 10 ms.** Part of the data shrank, conversions were added, and the matmuls were already on the reduced-precision tensor-core path because TF32 was applied first. That explains a small gain without any statement about round trips. The result is also order dependent: autocast measured before TF32 would show a different number.
- **Size of the effect.** 10 ms is two reporting steps on figures rounded to 5 ms, with no run-to-run spread.

**Suggested Improvement:** Replace the premise with what was observed, list which tensors became 16-bit (print dtypes at the block input, after layer norm, after the MLP, and at the logits), and present 'the number of round trips' as a hypothesis that the next section tests. Report autocast without TF32 as a control if the notebook allows.

Also at page 5: "pass stores activations in 16 bits instead of 32, so every matmul input".

Sources: https://docs.pytorch.org/docs/2.15/amp.html

**Suggested fix:** Autocast shrinks only the outputs of the matmul-type operations; layer norm, softmax, the loss and the weights stay float32, so the data moved was not halved. That alone may explain part of the small gain, and by now a

### C21 · MINOR · page 6

**Claim that PyTorch does not document autocast op coverage**

> PyTorch doesn't document clearly which ops autocast converts.

**Potential Concern (Outside fact):** `PyTorch doesn't document clearly which ops autocast converts.` The post has just told the reader exactly which ops stay in float32, and the PyTorch AMP documentation publishes explicit lists of the CUDA ops that autocast to float16 (matmul, linear, conv variants and others) and to float32 (softmax, layer_norm, cross_entropy and others); ops on neither list run in the dtype of their inputs. The statement is too strong as written.

**Suggested Improvement:** Replace the limitation with a pointer to the op reference. The reference list already includes the PyTorch AMP recipe.

Sources: https://docs.pytorch.org/docs/2.15/amp.html

**Suggested fix:** Which ops autocast converts is listed in the autocast op reference in the PyTorch AMP documentation; check it for any op your model relies on.

### C22 · MINOR · needs verification · page 7

**GELU 'eight kernels' in eager mode does not hold for nn.GELU**

> Eager PyTorch launches eight kernels, and each one reads from GPU memory and writes its result back.

**Potential Concern (Technical accuracy):** `The GELU ... is about eight small operations. Eager PyTorch launches eight kernels` is true only when the activation is written out as a Python expression. The built-in `nn.GELU` (with or without `approximate='tanh'`) is one native operation and one kernel in eager mode, so there is nothing for the compiler to fuse inside it. The post does not show its MLP code, so the reader cannot tell which case applies; the reference implementation the post says it follows uses the built-in module.

A strict reader will take the sentence as a statement about the model being timed and will find it incorrect. As an illustration of what fusion does to a chain of element-wise operations it is fine, but it should be labelled as such.

Separately, the page 8 diagram shows `· 0.044` while the formula on page 7 has `0.044715`.

**Suggested Improvement:** State whether the model's GELU is hand-written or the built-in module. If it is the built-in, present the formula as an illustration and pick a real chain from the model (for example the residual add followed by layer norm, or the attention scale, mask and softmax). Make the diagram constant match the text.

**To verify:** the author's MLP code, to see whether the model uses the built-in nn.GELU or a hand-written expression.

**Suggested fix:** Written out as separate tensor operations, this is eight kernels in eager PyTorch, and each one reads from GPU memory and writes its result back. (The built-in nn.GELU is already a single kernel; we use the expanded form here to illustrate what fusion does.)

### C23 · MAJOR · page 8

**Memory described (HBM, tens of GB) does not match the 8 GB test card**

> main memory, holds tens of gigabytes but sits off the compute chip

**Definitive Flaw (Hardware description):** `HBM, the GPU's main memory, holds tens of gigabytes but sits off the compute chip` is given as the reason fusion pays off, on a card the setup lists as `one RTX 5070 (8 GB)`.

- **Internal mismatch.** 8 GB against 'tens of gigabytes'. The description fits an A100-class accelerator, the card of the run the post follows, not the card measured.
- **Terminology.** HBM (High Bandwidth Memory) is a specific stacked-memory technology found on data-centre accelerators. GeForce cards use GDDR video memory. The principle the paragraph wants (device memory is far slower to reach than caches and registers, so each extra pass over a large tensor costs a full read and write) does not depend on the memory type, so the fix is a change of wording, but the term appears in the paragraph, the diagram labels and the diagram caption.
- **Stated capacity of the card.** The desktop RTX 5070 has 12 GB of GDDR7; 8 GB is the RTX 5070 Laptop GPU, a different part. The setup line should name the exact product, since it is the only memory figure a reader has for judging what batch size fits.
- **`A step that goes back to HBM after every operation spends most of its time moving data`** is asserted; no measurement of time spent in data movement is shown.

**Suggested Improvement:** Use 'GPU memory (VRAM)' in the text and the diagram, give the real capacity of the test card, and keep HBM only where an A100 is being discussed. Mark the 'most of its time' sentence as an expectation unless a profile is added.

Also at page 3: "Hardware: one RTX 5070 (8 GB). Windows, PyTorch 2.x. Windows needs".

Sources: https://www.techspot.com/specs/gpu/305060-nvidia-geforce-rtx-5070.html, https://techpowerup.com/review/nvidia-geforce-rtx-5070-founders-edition, https://laptopmedia.com/video-card/nvidia-geforce-rtx-5070-laptop/

**Suggested fix:** main memory (VRAM), holds [capacity of the test card] GB but sits off the compute chip

### C24 · MINOR · page 8

**torch.compile "largest single gain" vs TF32 saving more milliseconds**

> 1.74× from one line, the largest single gain in the loop.

**Potential Concern (Claim against chart):** `the largest single gain in the loop` holds for the ratio (1.74× against 1.43×) but not for time saved, where the chart gives TF32 `−75 ms` and torch.compile `−70 ms`. Page 14 and Conclusion 02 repeat the ranking in a section that counts milliseconds.

**Suggested Improvement:** Say which measure is meant wherever the ranking appears.

**Suggested fix:** 1.74× from one line, the largest single ratio in the loop (TF32 saved slightly more in absolute terms, 75 ms against 70 ms).

### C25 · MAJOR · page 8

**torch.compile gain attributed to fewer memory trips without isolating it**

> This is the cost autocast couldn't reach.

**Definitive Flaw (Causal attribution):** The 165 → 95 ms result is measured, but the explanation is at the level of *described*, while the wording (`This is the cost autocast couldn't reach`, `A step that goes back to HBM after every operation spends most of its time moving data`) needs *isolated* evidence.

- **Two causes, one number.** The section lists the interpreter and memory round trips as separate costs. The 70 ms is their sum plus anything else the compiler does (removal of per-op dispatch and allocation overhead, compilation of the backward pass, constant folding). Nothing shows how much of it is fusion.
- **The alternative is simple.** Per-operation launch and dispatch overhead is a fixed cost per op that is unrelated to memory bandwidth. Removing it would produce the same before/after pattern. The post's own glossary says each kernel launch `has fixed overhead`, so the text already contains the competing explanation.
- **Fusion has limited reach.** The matrix multiplies, which page 4 calls `most of the work`, are library calls that a compiler does not fuse with their neighbours; fusion applies mainly to chains of element-wise operations. The post does not show what share of the step those chains are.
- **Overstated mechanism.** `the network runs as a single unit with no Python in between` describes the best case. The training loop, optimizer step and data handling remain in Python, and the compiler can split a model into several compiled regions.
- **Protocol.** The figure is one step time with no repeat count or spread, and `start timing from the second step` does not say how many steps were averaged.

**Suggested Improvement:** Either measure the split (for example a profiler trace of kernel count and time in element-wise kernels before and after, or a GPU-utilisation trace), or soften the wording so the mechanism is offered as the likely explanation rather than the established one.

Also at page 8: "1.74× from one line, the largest single gain in the loop.".

**Suggested fix:** We did not separate the two effects, so this 70 ms is the combined saving from removing interpreter and per-op launch overhead and from fusing element-wise kernels.

### C26 · MINOR · page 8

**'Always' and 'only price is compile time' against the listed limitations**

> Always, unless debugging. Karpathy's view is that the only price is compile time.

**Potential Concern (Internal consistency):** The advice says `the only price is compile time`, and the next list reports that in the same source's run `compile broke text generation and the HellaSwag eval`, plus recompilation on shape changes and a Windows dependency. The two statements sit a few lines apart and do not agree. The view is also attributed to a named person without a pointer to where it was said.

**Suggested Improvement:** Narrow the advice to the case the post measured and point to the limitations.

Sources: https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py

**Suggested fix:** For the training loop, almost always, unless debugging. The main price is compile time; see the limitations below for generation, evaluation and changing input shapes.

### C27 · MINOR · page 9

**Attention matrix is not the largest temporary tensor; logits are larger**

> The attention matrix is the largest temporary tensor in the step.

**Definitive Flaw (Numerical claim):** With the post's own numbers the logits tensor is larger than the attention tensor.

- Attention, one layer, one sequence: `12 x 1024 x 1024 = 12.6M` numbers.
- Logits, one sequence: `1024 x 50,257 = 51.5M` numbers.

The logits are about four times larger, and page 4 already notes that `The largest is the classifier that turns 768 channels into 50,257 vocabulary scores`. The attention tensor is the largest only if summed across all 12 layers (about 151M numbers per sequence), or in the sense that it is the only one that grows with the square of the sequence length. The sequence length actually used for the timings is not stated anywhere, and the config on page 12 lists `block_size: int = 4096`, so the reader cannot tell which T the 95 → 85 ms result belongs to.

**Suggested Improvement:** Say what is actually distinctive about the attention matrix (it grows as T squared and is created in every layer) and state the batch size and sequence length used for timing.

**Suggested fix:** The attention matrix is the one temporary tensor that grows with the square of the sequence length, and every layer creates one.

### C28 · MINOR · page 10

**Paper's 7.6× is for attention alone, not a training step**

> (the paper reports up to 7.6×)

**Potential Concern (Citation scope):** `the paper reports up to 7.6×` gives no indication of what was 7.6× faster. In Dao et al. (2022) the figure is the speedup of the attention computation alone on GPT-2 (Figure 1); the abstract reports 3× end to end for GPT-2 at sequence length 1K. The post's own measurement for the whole step is 1.12×, so the unscoped figure overstates what a reader should expect.

**Suggested Improvement:** State what the figure measures and set it beside the post's own result.

Sources: https://arxiv.org/abs/2205.14135

**Suggested fix:** (the paper reports up to 7.6× for the attention computation alone; our whole training step gained 1.12×)

### C29 · MINOR · page 10

**Flash attention "10% faster" vs 1.12× in the table; mixed conventions**

> 10% faster, and the loss curve is unchanged apart from floating-point noise.

**Definitive Flaw:** The MEASURED box for flash attention says `10% faster`; the results table gives `1.12×` for the same 95 to 85 ms step.

- **Arithmetic:** 95 / 85 = 1.118 (12% faster); (95 - 85) / 95 = 10.5% (less time per step). The text reports the second and labels it as the first.
- **Convention:** TF32 and torch.compile are given as speed ratios (`1.43×`, `1.74×`), the other three as percentages, without saying whether a percentage is time saved or speed gained.
- **Precision:** the baseline is `~250 ms` in its own box and an exact 250 elsewhere, and every time is a multiple of 5 ms, so ratios such as `3.13×` carry more digits than the inputs.

**Suggested Improvement:** Use one convention in all five boxes (the table's ratio is the simplest) and say once how the times were rounded.

**Suggested fix:** 1.12× (12% faster), and the loss curve is unchanged apart from floating-point noise.

### C30 · MINOR · page 10

**"Ampere+" shorthand against "Ampere or newer" elsewhere**

> On Ampere+ with bfloat16, PyTorch picks the flash kernel automatically.

**Definitive Flaw:** The hardware condition is written out as "Ampere or newer" in four places and abbreviated to `Ampere+` once. The USE IT WHEN bullets for the same condition are also not parallel: a full sentence on page 4 ("The GPU is Ampere or newer ...") and a fragment on page 6 ("On Ampere or newer.").

**Suggested Improvement:** Use the spelled-out form here and one sentence shape for the condition in each box.

**Suggested fix:** On Ampere or newer with bfloat16, PyTorch picks the flash kernel automatically.

### C31 · MINOR · needs verification · page 10

**Flash kernel selection not confirmed on the author's Windows setup**

> On Ampere+ with bfloat16, PyTorch picks the flash kernel automatically.

**Potential Concern (Technical accuracy / platform):** The section attributes the 10 ms gain to FlashAttention, but `F.scaled_dot_product_attention` is a dispatcher, not a single algorithm. Which implementation runs depends on the PyTorch build and the inputs. The post's setup is Windows, where at least some official builds (a PyTorch 2.2 forum report) lacked the flash kernel and fell back to another path; whether current Windows wheels include it was not confirmed. Nothing in the post confirms which kernel ran.

A second point affects the attribution in the same way: this change was measured after `torch.compile` was already on, so the four-line version it is compared with was no longer running as four separate eager kernels, and the description `Each of the four lines writes that matrix to HBM, and the next line reads it back` describes the eager case, not the 95 ms state.

**Suggested Improvement:** Verify the back end on the measured machine (restrict the allowed back ends to flash only and confirm the call still succeeds), report the result, and word the claim by what was verified. If the flash kernel is unavailable, describe the gain as coming from PyTorch's fused attention implementation.

Sources: https://docs.pytorch.org/docs/2.15/generated/torch.nn.functional.scaled_dot_product_attention.html, https://discuss.pytorch.org/t/flash-attention-compilation-warning/196692

**To verify:** restrict the allowed attention back ends to flash only on the author's PyTorch build and confirm the call still succeeds.

**Suggested fix:** On Ampere or newer with bfloat16, PyTorch can pick the flash kernel automatically when the build includes it; check which back end is used on your platform.

### C32 · MINOR · page 11

**Capital after the colon in one section title only**

> Padding the vocabulary: Nice numbers for

**Definitive Flaw:** The section 5 title capitalises the word after the colon (`Nice`); the other four section titles do not.

**Suggested Improvement:** Lower-case "nice" to match.

**Suggested fix:** Padding the vocabulary: nice numbers for

### C33 · MINOR · page 11

**Token embedding and classifier are one tied matrix in GPT-2, not two**

> It also sets the size of the two largest matrices in the model: the token

**Definitive Flaw:** In GPT-2, and in the build-nanogpt code the post follows, the token embedding and the output classifier are the same tensor (weight tying). `the two largest matrices` should be one matrix used in two places, and only the classifier use is a matrix multiply; the embedding is a lookup, which the tiling argument does not cover.

Sources: https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py

**Suggested fix:** It also sets the size of the largest matrix in the model, which GPT-2 shares between the token

### C34 · MINOR · page 12

**Config class and field names: GPTconfig, GPT(config), n_layers vs n_head**

> class GPTconfig:

**Definitive Flaw:** Naming in the config listing is uneven:

- **Class name:** `GPTconfig` (page 11 caption, page 12 listing) is not CamelCase; Python convention and the source the post follows use `GPTConfig`.
- **Field names:** `n_layers` is plural while `n_head` is singular in the same listing. Use one form for both.

Locations: page 11 (`GPTconfig · python`), page 12 (`class GPTconfig:`, `n_layers: int = 12`, `n_head: int = 12`), and the instance `GPT(config)` on page 8.

**Suggested Improvement:** Rename the class in the caption and listing, and make the two count fields parallel (`n_layer`/`n_head`).

Also at page 8: "model = GPT(config).to(device)".

Sources: https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py

**Suggested fix:** class GPTConfig:

### C35 · MAJOR · page 12

**Config block_size 4096 vs T = 1024 and GPT-2 124M**

> block_size: int = 4096

**Definitive Flaw (Code against prose):** The config listing gives `block_size: int = 4096`, while the flash attention section reasons from `At T = 1024` and the setup describes the model as `GPT-2 124M`.

- **Arithmetic:** 1024² = 1,048,576 (the post's `about a million`); 4096² = 16,777,216.
- **Model size:** a 4096-row position embedding adds 3072 x 768 = 2,359,296 parameters, giving about 126.8M rather than 124M.
- **Setup gap:** the sequence length and batch size used for timing are not given on page 3, so the two values cannot be reconciled from the text.

**Suggested Improvement:** Make the listing match the model that was timed, and state the sequence length and batch size once in the Setup section.

Sources: https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py

**Suggested fix:** block_size: int = [value used for the timed runs; 1024 if GPT-2 124M as described]

### C36 · MAJOR · page 12

**5 ms vocabulary gain equals the rounding step of the timings**

> The model now does slightly more work and runs 6% faster.

**Potential Concern (Measurement resolution):** The post reports `85 → 80 ms` and concludes `The model now does slightly more work and runs 6% faster.`

- **Resolution.** Every step time in the post is a multiple of 5 ms. With figures rounded to that step, a 5 ms difference is one unit of resolution: the underlying change could be near zero or about 10 ms. The same applies, less severely, to the two 10 ms steps (autocast and flash attention).
- **No spread.** The post does not say how many steps were averaged or how much a single configuration varies from step to step. On a card that also drives the display, a few ms of step-to-step variation is ordinary. Changing the vocabulary size also forces a fresh compilation, so the two timings come from separately compiled graphs.
- **Mechanism asserted, not shown.** `GPU kernels cut matrices into tiles whose sides are powers of two` and `the leftover goes through a separate, slower pass` are stated as how the libraries work, with no reference and no isolating measurement (for example timing the classifier matmul alone at 50,257 and 50,304 columns). `Newer versions handle the leftover pass better` is likewise unsupported.
- **Outside figure.** `Karpathy saw about 30% on PyTorch 2.3.1 and earlier` carries no reference. The chapter list of the cited video gives 96 ms before and 93 ms after the vocabulary change, about 3%, and no source was found for 30% or for the PyTorch 2.3.1 remark. If the reference gain was about 3%, the sentence explaining the difference by PyTorch version has nothing to explain.

**Suggested Improvement:** Report the mean and spread over a stated number of steps for both vocabulary sizes, to at least 1 ms. If the difference is within the spread, say that the change made no measurable difference on this card and keep it as a low-cost habit, not a measured gain. Time the output-layer matmul in isolation if the tiling explanation is kept, and cite the source of the 30% figure.

Sources: https://summify.io/discover/let-s-reproduce-gpt-2-124m, https://classcentral.com/classroom/youtube-let-s-reproduce-gpt-2-124m-295231

**Suggested fix:** The model now does slightly more work and the step time went from [mean ± spread] ms to [mean ± spread] ms over [N] steps.

### C37 · MINOR · page 12

**'About 30%' attributed to Karpathy; the cited video shows about 3% (96 to 93 ms)**

> about 30% on PyTorch 2.3.1 and earlier.

**Potential Concern (outside fact):** `Karpathy saw about 30% on PyTorch 2.3.1 and earlier. Newer versions handle the leftover pass better, so the gain is smaller but still there.` The figure has no reference. The chapter list of the cited video gives 96 ms before and 93 ms after the vocabulary change, about 3%, which also fits the 93 ms end point quoted on page 14 (a 30% gain would need a step of roughly 121 to 133 ms before it). No source was found for 30% or for the PyTorch 2.3.1 remark. If the reference gain was about 3%, the post's 6% is not smaller than it, and the sentence about newer versions has nothing to explain.

**Suggested Improvement:** Give the before and after step times from the source with a timestamp or link, and either cite or remove the statement about newer versions.

Sources: https://summify.io/discover/let-s-reproduce-gpt-2-124m, https://classcentral.com/classroom/youtube-let-s-reproduce-gpt-2-124m-295231

**Suggested fix:** about 3% (96 → 93 ms, per the video's chapter list) in his run. [Also remove or source the next sentence about newer versions.]

### C38 · MINOR · page 12

**GPT-2 XL's 25 heads is a poor example of an awkward matmul dimension**

> Not every odd number is easy to fix. GPT-2 XL has 25 heads, and changing

**Definitive Flaw (technical precision):** The USE IT WHEN list names `head count` as a dimension that `feeds a matmul`, and the limitation cites GPT-2 XL's 25 heads as an odd number that cannot be fixed. The number of heads is not a matrix side in the attention product; the per-head width is, and for GPT-2 XL it is 1600 / 25 = 64. The example therefore illustrates a config that is already 'nice' on the dimension that matters. The rule `doesn't divide by a power of two` also needs a threshold: 50,257 fails because it is odd, but 768 is divisible by 256 and not by 512, and the post does not say which side of the rule that falls on.

**Suggested Improvement:** Drop head count from the list, replace the XL example or remove it, and state the test concretely (for instance, divisible by 64 or 128).

### C39 · MINOR · page 12

**Glossary terms that the body text never uses**

> Boundary kernel

**Potential Concern:** Four glossary headwords do not appear in the sections they close:

- **Boundary kernel** (page 12): the text calls it "a separate, slower pass" and "the leftover pass".
- **Materialize** (page 11): the text says "writing that T×T matrix to memory".
- **FLOPs** (page 11): the text says "more arithmetic".
- **Gradient scaler** (page 7): the text uses the class name `GradScaler`.

**Suggested Improvement:** Either use each term once in the body where the concept is introduced, or rename the glossary entry to the wording the body uses (for example the entry below).

**Suggested fix:** Leftover pass (boundary kernel)

### C40 · MINOR · page 13

**Results table and chart label the same rows differently**

> vocab → 50304

**Definitive Flaw:** Three of the six rows are labelled differently in the table and in the chart beneath it: `TF32 matmuls` / `TF32`, `Flash attention` / `flash attention` (capitalisation), and `vocab → 50304` / `vocab 50304`. Outside code, the vocabulary size is written `50,304` in prose but `50304` in both labels.

**Suggested Improvement:** Use one label per row in both places, for example "TF32", "Flash attention" and the label below.

**Suggested fix:** vocab → 50,304

### C41 · MINOR · page 14

**85/85 ms split: grouping and 'behave differently' contradict the post's own numbers**

> The 170 ms saved splits evenly: 85 ms from the two precision changes and 85

**Definitive Flaw (internal consistency):** The sums are right, but three statements in this paragraph do not survive a comparison with the rest of the post.

- **Category count.** `the three memory-traffic changes` counts vocabulary padding as memory traffic. Its own section is labelled `OPTIMIZATION 5 · NICE NUMBERS` and explains the gain by tile alignment. Under the post's own labels the split is 85 / 80 / 5 ms, not 85 / 85.
- **'They behave differently'.** `Precision gave one big jump with TF32 and then stalled. The memory-traffic changes kept paying off`. The savings are 75 then 10 ms for precision, and 70 then 10 then 5 ms for the other group. Both are one large step followed by small ones.
- **Largest gain.** `torch.compile alone saving 70 ms` is presented as the standout, yet TF32 saved 75 ms. torch.compile is largest only as a ratio (1.74× against 1.43×), and each ratio depends on what was applied before it.
- **Chart.** The caption `Green bars are the memory-traffic changes` refers to bars that are not visible in the PDF, where only the torch.compile label is green.

**Suggested Improvement:** State the split using the post's own three labels, drop the contrast the data does not show, say that torch.compile is the largest gain as a ratio while TF32 is the largest in milliseconds, and note that the split reflects this particular order of changes. Check that the chart bars render in the exported file.

**Suggested fix:** Of the 170 ms saved, 85 ms came from the two precision changes, 80 ms from the two memory-traffic changes and 5 ms from vocabulary padding. [Replaces the whole sentence through "memory-traffic changes."]

### C42 · MINOR · needs verification · page 14

**A100 comparison (11x vs 3.1x) lacks workload parity**

> float32 baseline started much slower

**Potential Concern (Comparison validity):** The post says `Karpathy's A100 went from 1000 ms to 93 ms, about 11× against our 3.1×. His float32 baseline started much slower, and the A100's roughly 2 TB/s of memory bandwidth leaves more room for each change to help.`

- **Implied figure.** 1000 ms on an A100 against 250 ms on an RTX 5070 means the data-centre card was 4x slower at baseline. The post notes this (`started much slower`) but does not say why. The simplest explanation is that the A100 step did more work: a larger batch, a longer sequence, or both. The post gives neither for its own run nor for the reference run.
- **Why it matters for the argument.** Step time in ms is only comparable at equal tokens per step. A larger batch also changes the mix: fixed per-kernel and Python overhead becomes a smaller share and matmul time a larger share, which by itself would make TF32 and the other changes look bigger. That alternative needs no appeal to bandwidth.
- **Direction of the bandwidth argument.** The post's thesis is that a loop limited by memory gains little from cheaper arithmetic. On that reading, more bandwidth is a reason the A100 is less memory bound, which is a claim about the A100's workload, not evidence about the RTX 5070 loop. The sentence is offered as an explanation without a measurement on either card.
- **'The pattern is the same on both cards'** rests on the per-step figures of the reference run, which are not quoted or referenced here.

**Suggested Improvement:** Give batch size and sequence length for both runs and compare in tokens per second, or drop the cross-card ratio. If the reference run used a different batch, say so and remove the bandwidth explanation. Quote the reference run's per-step figures with a source if the 'same pattern' sentence is kept.

Also at page 14: "bandwidth leaves more room for each change to help.".

Sources: https://images.nvidia.com/data-center/a100/a100-datasheet.pdf, https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/a100-80gb-datasheet-update-a4-nvidia-1485612-r12-web.pdf, https://summify.io/discover/let-s-reproduce-gpt-2-124m

**To verify:** the batch size and sequence length used in the reference run's timing section and in the author's notebook.

**Suggested fix:** float32 baseline started much slower (his step processed [B × T] tokens, ours [B × T])

### C43 · MAJOR · page 14

**Memory-bound diagnosis fails its own first prediction (autocast)**

> That one number predicts the rest.

**Definitive Flaw (Causal inference):** The summary box says `That one number predicts the rest.` Read against the post's own sequence, it does not.

- **What the diagnosis predicts.** On pages 4-5 'memory bound' means bandwidth: `every number is still a 4-byte float32 that has to travel`, `Capped by memory bandwidth`, and the bridge sentence `If moving bytes is the bottleneck, the next step is to move fewer of them.` That is a forecast that halving the bytes will help a lot.
- **What was measured.** Page 6: `175 → 165 ms`, with the post's own comment `Halving the activations should have helped more`. The forecast failed.
- **What the post does next.** It introduces a second bottleneck, `the number of memory round trips`, and page 14 folds both under the single label 'memory bound'. Bytes per trip (bandwidth) and number of trips (per-kernel launch overhead and extra passes over the data) are different limits with different remedies. A loop limited by launch overhead and Python dispatch is usually called overhead bound, and it would show the same 1.43x, the same small autocast gain and the same large compile gain without any tensor core 'waiting for data'.
- **Single ordering.** Every 'clue' comes from one ordering of the changes, each timed once. If compile were applied first, the TF32 and autocast gains would be measured against a different remainder and the story could read differently.

A strict reader would say the sequence is consistent with the memory-traffic account but equally consistent with a plain overhead account, and that the TF32 ratio alone predicts neither.

**Suggested Improvement:** State the diagnosis at the level the evidence supports (a hypothesis that fits the sequence), separate 'bytes moved' from 'number of kernel passes' as two candidate bottlenecks, and say plainly that the autocast result argued against the first. To make the stronger wording hold, show a profiler breakdown of one step (time in matmul kernels, element-wise kernels, and CPU-side dispatch) before and after each change, or repeat the ladder in a different order.

Also at page 14: "Getting 1.4× from TF32 instead of 8× is the diagnosis: the loop is memory"; page 6: "different cost dominates. Eager PyTorch launches each small element-wise".

**Suggested fix:** The TF32 result was the first clue, and the autocast result revised it: halving the bytes barely helped, which suggests the limit is less how many bytes move than how many separate passes the step makes over them.

### C44 · MINOR · needs verification · page 14

**Conclusions cover four of five changes; pre-Ampere advice skips float16 autocast**

> If not, go straight to compile.

**Potential Concern (summary against body):**

- **Five lines, four in the rules.** Vocabulary padding does not appear in either conclusion. If the author regards it as marginal, saying so would be consistent with the 5 ms result.
- **Older cards.** `If not, go straight to compile` omits float16 autocast with a GradScaler, which the post itself describes on page 5. Whether that pays on a given pre-Ampere card depends on its hardware, which I have not verified per generation, so this is a prompt to the author, not a correction.
- **Scope.** `torch.compile is the biggest single gain available` holds as a ratio in this run and this order; it is stated as a general fact.

**Suggested Improvement:** Add a third rule for vocabulary padding (or a sentence that it is optional), mention float16 autocast for older cards, and tie 'biggest single gain' to this run.

**To verify:** tensor-core support by GPU generation, to see whether float16 autocast pays on a given pre-Ampere card.

**Suggested fix:** If not, try float16 autocast with a GradScaler, then compile.

### C45 · SUGGESTION · page 15

**"References:" label style and unidentified source types in the credits**

> References:

**Potential Concern:** Three small points in the closing card: the `References:` label is the only heading-like line with a colon and without heading styling; the credit sentence identifies `build-nanogpt` as a repository but does not say that `Let's reproduce GPT-2 (124M)` is a video lecture; and one of the five reference entries has an explanatory tail where the others are author, year, title only.

**Suggested Improvement:** Style the label like "Related reading" and drop the colon; write "Andrej Karpathy's video lecture Let's reproduce GPT-2 (124M) and his build-nanogpt repository"; keep the reference entries to one pattern.

**Suggested fix:** References
