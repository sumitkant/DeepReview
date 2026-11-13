# Stage 4 synthesis: merge verified findings into 4_review.json and review.md.
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
findings = {x["index"]: x for x in json.loads((HERE / "2_findings.json").read_text(encoding="utf-8"))}
verdicts = {x["index"]: x for x in json.loads((HERE / "3_verdicts.json").read_text(encoding="utf-8"))["verdicts"]}
document = (HERE / "document.txt").read_text(encoding="utf-8")
search = (HERE / "search_results.md").read_text(encoding="utf-8")

# Merge groups; the first index of each group is the lead.
GROUPS = [
    [24, 14, 64, 47],            # memory-bound narrative
    [32, 44, 48],                # Amdahl alternative and the borrowed 8x ceiling
    [18, 45],                    # 1.5-3x expectation vs 1.43x
    [46, 17, 26, 36, 57, 65],    # accuracy claims without data
    [30, 16, 55, 38],            # HBM / tens of GB vs the 8 GB card
    [15, 67],                    # block_size 4096
    [56, 23, 28],                # largest temporary tensor
    [53, 29],                    # compile gain attribution
    [21, 59],                    # largest single gain
    [63, 19],                    # 85/85 split
    [20, 60],                    # 10% vs 1.12x
    [25, 68],                    # A100 comparison
    [27, 66],                    # 5 ms vocabulary gain
    [34, 33],                    # setup / protocol
    [31, 50],                    # autocast premise
    [1, 42],                     # "modfications"
    [3, 43],                     # TL;DR headline sentence
    [7, 22],                     # config naming
    [0], [2], [4], [5], [6], [8], [9], [10], [11], [12], [13], [35], [37], [39], [40], [41],
    [49], [51], [52], [54], [58], [61], [62], [69], [70], [71], [72],
]

U = {
    "techspot": "https://www.techspot.com/specs/gpu/305060-nvidia-geforce-rtx-5070.html",
    "tpu": "https://techpowerup.com/review/nvidia-geforce-rtx-5070-founders-edition",
    "a100": "https://images.nvidia.com/data-center/a100/a100-datasheet.pdf",
    "a100_80": "https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/a100-80gb-datasheet-update-a4-nvidia-1485612-r12-web.pdf",
    "amp": "https://docs.pytorch.org/docs/2.15/amp.html",
    "sdpa": "https://docs.pytorch.org/docs/2.15/generated/torch.nn.functional.scaled_dot_product_attention.html",
    "flash": "https://arxiv.org/abs/2205.14135",
    "summify": "https://summify.io/discover/let-s-reproduce-gpt-2-124m",
    "classcentral": "https://classcentral.com/classroom/youtube-let-s-reproduce-gpt-2-124m-295231",
    "laptop": "https://laptopmedia.com/video-card/nvidia-geforce-rtx-5070-laptop/",
    "nanogpt": "https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py",
    "forum": "https://discuss.pytorch.org/t/flash-attention-compilation-warning/196692",
}
# Grounding URLs by lead index (only sources present in search_results.md).
GROUNDING = {
    30: ["techspot", "tpu", "laptop"],
    32: ["a100"],
    25: ["a100", "a100_80", "summify"],
    69: ["summify", "classcentral"],
    27: ["summify", "classcentral"],
    51: ["amp"],
    31: ["amp"],
    58: ["sdpa", "forum"],
    61: ["flash"],
    62: ["nanogpt"],
    71: ["nanogpt"],
    15: ["nanogpt"],
    7: ["nanogpt"],
    52: ["nanogpt"],
}
# "To verify" sentences for needs_verification comments, taken from the verifier's reasons.
TO_VERIFY = {
    37: "the Python version used and its release notes for the resolution of time.time() on Windows; rerunning the ladder with time.perf_counter() and the batch moved to the device before t0 would show whether the figures change.",
    49: "the TF32 section of the cited video, to see whether the 60% figure is Karpathy's remark.",
    52: "run the line with device = 'cuda:0' (or a torch.device object) and see whether torch.autocast accepts it.",
    54: "the author's MLP code, to see whether the model uses the built-in nn.GELU or a hand-written expression.",
    58: "restrict the allowed attention back ends to flash only on the author's PyTorch build and confirm the call still succeeds.",
    72: "tensor-core support by GPU generation, to see whether float16 autocast pays on a given pre-Ampere card.",
}

REVIEW_MARKDOWN = """### Summary

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
"""

RANK = {"SUGGESTION": 0, "MINOR": 1, "MAJOR": 2, "CRITICAL": 3}


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def final(i, field):
    v = verdicts[i].get(field)
    if v in (None, ""):
        v = findings[i].get(field)
    return v


# Page texts for ordering.
pages = {}
for m in re.finditer(r"\[page (\d+)\]\n(.*?)(?=\n\[page \d+\]|\Z)", document, re.S):
    pages[int(m.group(1))] = norm(m.group(2))
doc_norm = norm(document)

TV_RE = re.compile(r"\n*\*\*To (?:settle|verify):\*\*\s*(.*?)\s*\Z", re.S)

comments = []
for group in GROUPS:
    lead = group[0]
    f = findings[lead]
    severity = final(lead, "severity")
    assert RANK[severity] == max(RANK[final(i, "severity")] for i in group), group
    nv = bool(verdicts[lead].get("needs_verification"))
    label = final(lead, "label")
    body = final(lead, "body_markdown").strip()

    # Label at the start of the body, using the verifier's final label.
    if re.match(r"\*\*(Definitive Flaw|Potential Concern)", body):
        body = re.sub(r"^\*\*(Definitive Flaw|Potential Concern)", "**" + label, body, count=1)
    else:
        body = "**%s:** %s" % (label, body)

    # Pull any existing To verify / To settle sentence off the end.
    to_verify = None
    m = TV_RE.search(body)
    if m:
        to_verify = m.group(1)
        body = body[: m.start()].rstrip()

    # Other locations for merged groups (distinct quotes only).
    lead_q = norm(f["quote"])
    seen = [lead_q]
    others = []
    for i in group[1:]:
        q = norm(findings[i]["quote"])
        if any(q in s or s in q for s in seen):
            continue
        seen.append(q)
        others.append('page %d: "%s"' % (findings[i]["page"], q[:80]))
    if others:
        body += "\n\nAlso at " + "; ".join(others) + "."

    urls = [U[k] for k in GROUNDING.get(lead, [])]
    for u in urls:
        assert u in search, u
    if urls:
        body += "\n\nSources: " + ", ".join(urls)

    if nv:
        assert severity in ("MINOR", "SUGGESTION"), group
        tv = TO_VERIFY.get(lead) or to_verify
        assert tv, "no To verify text for %d" % lead
        body += "\n\n**To verify:** " + tv

    suggested = final(lead, "suggested_edit") or ""
    if not suggested:
        for i in group[1:]:
            if norm(findings[i]["quote"]) == lead_q and final(i, "suggested_edit"):
                suggested = final(i, "suggested_edit")
                break

    page = f["page"]
    pos = pages.get(page, "").find(lead_q)
    comments.append({
        "severity": severity,
        "needs_verification": nv,
        "summary": final(lead, "summary"),
        "body_markdown": body,
        "suggested_edit": suggested,
        "location": {"page": page, "quote": {"exact": f["quote"]}},
        "grounding_urls": urls,
        "merged_from": sorted(group),
        "_pos": pos if pos >= 0 else 10 ** 9,
    })

comments.sort(key=lambda c: (c["location"]["page"], c["_pos"], -RANK[c["severity"]]))
out_comments = []
for n, c in enumerate(comments, 1):
    c.pop("_pos")
    out_comments.append({"comment_id": "C%d" % n, **c})

review = {"review_markdown": REVIEW_MARKDOWN, "anchored_comments": out_comments}
(HERE / "4_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

# review.md
lines = [REVIEW_MARKDOWN.rstrip(), "", "## Detailed feedback", ""]
for c in out_comments:
    flag = " · needs verification" if c["needs_verification"] else ""
    lines.append("### %s · %s%s · page %d" % (c["comment_id"], c["severity"], flag, c["location"]["page"]))
    lines.append("")
    lines.append("**%s**" % c["summary"])
    lines.append("")
    lines.append("> " + norm(c["location"]["quote"]["exact"]))
    lines.append("")
    lines.append(c["body_markdown"])
    lines.append("")
    if c["suggested_edit"]:
        lines.append("**Suggested fix:** " + c["suggested_edit"])
        lines.append("")
(HERE / "review.md").write_text("\n".join(lines), encoding="utf-8")

# Validation
errors = []
seen = []
for c in out_comments:
    if norm(c["location"]["quote"]["exact"]) not in doc_norm:
        errors.append("quote not found: %s %r" % (c["comment_id"], c["location"]["quote"]["exact"][:60]))
    if norm(c["location"]["quote"]["exact"]) not in pages.get(c["location"]["page"], ""):
        errors.append("quote not on stated page: %s" % c["comment_id"])
    if c["needs_verification"]:
        if c["severity"] in ("CRITICAL", "MAJOR"):
            errors.append("NV too severe: %s" % c["comment_id"])
        last = c["body_markdown"].rstrip().split("\n\n")[-1]
        if not last.startswith("**To verify:**"):
            errors.append("NV lacks To verify ending: %s" % c["comment_id"])
    seen.extend(c["merged_from"])
if sorted(seen) != list(range(73)):
    errors.append("index coverage wrong")
sys.stdout.reconfigure(encoding="utf-8")
counts = {}
for c in out_comments:
    counts[c["severity"]] = counts.get(c["severity"], 0) + 1
print("comments:", len(out_comments), counts, "needs_verification:", sum(c["needs_verification"] for c in out_comments))
print("no suggested_edit:", [c["comment_id"] for c in out_comments if not c["suggested_edit"]])
print("ERRORS:", errors if errors else "none")
