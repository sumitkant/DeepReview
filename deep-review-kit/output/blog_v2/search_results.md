# Search results (outside evidence gathered 13 Nov 2026)

1. RTX 5070 (desktop): 12 GB GDDR7, 192-bit bus, 672 GB/s memory bandwidth, 48 MB L2 cache, 6144 CUDA cores, launched 2025. It does not use HBM. (Not searched, reviewer knowledge only: the GeForce RTX 5070 Laptop GPU is a different part with 8 GB; treat as likely but unconfirmed.)
   - https://www.techspot.com/specs/gpu/305060-nvidia-geforce-rtx-5070.html
   - https://techpowerup.com/review/nvidia-geforce-rtx-5070-founders-edition

2. NVIDIA A100 datasheet: peak FP32 19.5 TFLOPS; peak TF32 156 TFLOPS (312 with sparsity). Memory bandwidth 1,555 GB/s (40 GB, HBM2) and 2,039 GB/s (80 GB, HBM2e).
   - https://images.nvidia.com/data-center/a100/a100-datasheet.pdf
   - https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/a100/pdf/a100-80gb-datasheet-update-a4-nvidia-1485612-r12-web.pdf

3. torch.set_float32_matmul_precision (PyTorch docs): "highest" (default) uses float32 (24 mantissa bits, 23 stored) internally. "high" uses TensorFloat32 (10 mantissa bits stored) or treats each float32 as the sum of two bfloat16 numbers (about 16 mantissa bits) if a fast algorithm exists, else behaves as "highest". "medium" uses bfloat16 (8 mantissa bits, 7 stored) internally if a fast algorithm exists, else behaves as "high". It does not change convolution precision.
   - https://docs.pytorch.org/docs/2.15/generated/torch.set_float32_matmul_precision.html

4. PyTorch Automatic Mixed Precision docs: the page publishes explicit lists of "CUDA Ops that can autocast to float16" (includes matmul, mm, bmm, linear, addmm, conv variants) and "CUDA Ops that can autocast to float32" (includes softmax, log_softmax, layer_norm, group_norm, cross_entropy, nll_loss, mse_loss, pow, exp, log, sum, prod, norm, rsqrt, reciprocal and others). Ops on neither list run in the dtype of their inputs. GradScaler is documented for float16 training; the page's bfloat16 examples use autocast alone.
   - https://docs.pytorch.org/docs/2.15/amp.html

5. torch.nn.functional.scaled_dot_product_attention (PyTorch docs): three implementations (FlashAttention-2, memory-efficient attention, a C++ implementation of the standard formulation). All enabled by default; the function "attempts to automatically select the most optimal implementation based on the inputs". Fused kernels are CUDA only and each has input limitations the page does not list. "An error is thrown if both attn_mask and is_causal are set." Only the attention output is returned, not the weights.
   - https://docs.pytorch.org/docs/2.15/generated/torch.nn.functional.scaled_dot_product_attention.html

6. FlashAttention (Dao, Fu, Ermon, Rudra, Ré, 2022, arXiv 2205.14135): "up to 7.6×" is the speedup of the attention computation alone on GPT-2 (Figure 1). End to end the abstract reports 3× on GPT-2 (sequence length 1K) against HuggingFace and Megatron-LM baselines, and 15% on BERT-large. The paper frames the saving as not reading and writing the N×N attention matrix to HBM.
   - https://arxiv.org/abs/2205.14135

7. Karpathy, "Let's reproduce GPT-2 (124M)" (2024), chapter list gives ms per step on his hardware: 1000 ms baseline, 333 ms with TF32, 300 ms with bfloat16 autocast, 130 ms with torch.compile, 96 ms with flash attention, 93 ms with vocab 50257 → 50304. So in the video the vocabulary change is 96 → 93 ms (about 3%). Stepwise ratios: 3.0×, 1.11×, 2.31×, 1.35×, 1.03×; total about 10.75×. No source found for "about 30%" from vocabulary padding or for "PyTorch 2.3.1".
   - https://summify.io/discover/let-s-reproduce-gpt-2-124m
   - https://classcentral.com/classroom/youtube-let-s-reproduce-gpt-2-124m-295231

8. GeForce RTX 5070 Laptop GPU: a different, cut-down part with 8 GB GDDR7 on a 128-bit bus; sources give 384 to 448 GB/s bandwidth. So "RTX 5070 (8 GB)" matches the laptop GPU, not the 12 GB desktop card.
   - https://laptopmedia.com/video-card/nvidia-geforce-rtx-5070-laptop/

9. karpathy/build-nanogpt train_gpt2.py (current master): `use_compile = False # torch.compile interferes with HellaSwag eval and Generation. TODO fix` (compile is switched off for the whole run there). `B = 64 # micro batch size`, `T = 1024 # sequence length` in the final script (the video's speed section used a smaller batch; not confirmed here). GPTConfig fields are `block_size: int = 1024`, `vocab_size: int = 50257`, `n_layer`, `n_head`, `n_embd`; the model is built with `GPTConfig(vocab_size=50304)`. Weight tying is present: `self.transformer.wte.weight = self.lm_head.weight`. Timing uses `time.time()` with `torch.cuda.synchronize()`. Attention: `F.scaled_dot_product_attention(q, k, v, is_causal=True) # flash attention`. `torch.set_float32_matmul_precision('high')`; `torch.autocast(device_type=device_type, dtype=torch.bfloat16)`.
   - https://raw.githubusercontent.com/karpathy/build-nanogpt/master/train_gpt2.py

10. Flash attention on Windows: PyTorch forum thread (PyTorch 2.2, Windows) reports the warning "Torch was not compiled with flash attention" from scaled_dot_product_attention, with a reply that FlashAttention V2 is not available in Windows builds (PyTorch issue #108175); the function still runs using another backend. Whether current Windows wheels include the flash kernel was not confirmed.
   - https://discuss.pytorch.org/t/flash-attention-compilation-warning/196692

Still not searched: the "about 60%" tensor-core utilisation figure, time.time() resolution on Windows, Tiny Shakespeare token count, GPT-2 XL head count, triton-windows version pin.
