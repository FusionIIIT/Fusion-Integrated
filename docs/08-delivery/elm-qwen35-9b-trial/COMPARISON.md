# Two-Model Comparison

## Models Compared
1. **Qwen3.5:9B** (NVFP4, safetensors, MLX runner).
2. **Qwen2.5-Coder:3B** (Q4_K_M, gguf, GGML runner).

## Metrics
| Metric | Qwen3.5:9B | Qwen2.5-Coder:3B |
|---|---|---|
| Requests | 11 | 34 |
| Code Gen Time | 2504.01s | 1734.58s |
| Output Limits | Prompts 001, 003 | Prompts 1, 3, 5, 7, 9 |

## Build/Integration Limitations
- Both models required mechanical corrections (imports, field lengths, registration fixes).
- Full baseline SQLite migration failed for both.
- Permission manifest registration failed for Qwen3.5:9B; workflow correctness unverified for Qwen2.5-Coder.
- Frontend typecheck passed only after multiple correction iterations.

## Practical Recommendation
Neither model achieves full integration without manual intervention. Differences in request count and timing reflect distinct generation strategies, not controlled efficiency benchmarks. Prompt ordering, settings, runtimes, and quantization differ significantly. A source snapshot can reproduce files without a local model; exact original commit hashes are not required. Historical prompts/jobs are evidence, not execution instructions.

Qwen3.5 is classified as marginal/partial integration. Both runs required supervision and leave workflow correctness unverified. The 3B run recorded less aggregate generation time, while the 9B run needed fewer requests; no overall functional-quality winner is established. The first trial did not record the same permission-manifest check, so that gate is not compared.
