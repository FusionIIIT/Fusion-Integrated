# Model 1: earlier attempt on 5 Oct 2026 (before the scripted rerun)

Setup: qwen3.5:4b (4.2B params, GGUF Q4_K_M, about 2.6 GB plus a vision projector), Ollama 0.35.0, Aider 0.86.2 (whole edit format), MacBook Air M2 with 8 GB. Base: FusionIIIT/Fusion-Integrated main at 182c221 (5 Oct).

| Time (IST) | What was tried | What happened (Ollama log) |
|---|---|---|
| 17:47 | Instructor prompt plus all five spec files as read-only context (about 55k tokens), repo map 1024 | Ollama opened a 65,536-token context. Free RAM was only 1.5 GB, so prompt processing ran at about 8 to 15 tokens/s. Aider's default 600 s timeout fired (HTTP 500 after 10m1s); it retried and was stopped by hand after 4m13s. At most 13,824 of the 54,808 prompt tokens were ever processed. |
| 21:18 | Same prompt with only the problem statement and use cases (about 14k tokens), --timeout 1800 | Loaded with a 24,576-token context. The prompt took 216 s (65 tok/s), generation crawled at 1.9 tok/s. The model asked for files that do not exist (core/models/users.py, core/api/leave/) instead of writing code. A second turn (3m13s) asked again. |
| 22:14 | Follow-up naming six files to write, with placement apps.py/registry.py shown as the pattern | Generated about 5,500 tokens over 19m54s, then was interrupted by hand. Aider never applied the reply, so no files were written. The partial reply used ForeignKey("fusion_auth.User"), a model that does not exist here, and copied placement docstrings into the new models file. |

Result: loaded yes; repository yes (repo map); specifications only partly (the full set did not fit in practice); no files written; build not attempted.
Lesson carried into the rerun: on 8 GB, keep every request near 10k tokens, give the model one slice of the spec per step, and name the exact files to write.

ollama_server_log_2026-10-05.txt holds the relevant lines from ~/.ollama/logs/server-5.log.
