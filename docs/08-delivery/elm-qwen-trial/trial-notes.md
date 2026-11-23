# Local model trial observations

- Candidate: `qwen2.5-coder:3b`, 3.1B, Q4_K_M, Ollama 0.40.3.
- Hardware: Apple M4, 16 GB unified memory. Ollama reported 100% GPU execution and a 32,768-token context.
- Prompt 001: 19,203 input tokens; 8,192 generated tokens; 402.12 seconds. The response ended at the output limit with incomplete JSON. No application files were applied.
- Workaround: split initial generation into smaller file batches, request data-only compact models, and remove duplicated AFR decomposition from subsequent context while preserving consolidated requirements and rules.
- Functional correctness has not been assessed. Checks are limited to compilation, configuration, interfaces, module/route registration and schema integration.
- Prompt 002: compact model-only retry succeeded; 12714 input tokens, 1351 output tokens, 77.81 seconds. Produced 13 model classes in 142 source lines. Python syntax compilation passed.
- Prompt 003: 312.32 seconds, 6000 generated tokens; final contracts.py string was truncated. Mechanically recovered 5 preceding complete source files unchanged; the incomplete contracts file remains unapplied.
- Prompt 005: broad service generation hit its 6500-token limit after 334.38 seconds and did not return a complete file. No service logic was applied. Subsequent initial-generation prompts use small, focused outputs and per-component specification context.
- Prompt 006 returned the unchanged, incorrectly shaped registry.py despite the interface-correction request. This instruction-following failure is preserved. Subsequent prompts put reference material first and repeat the explicit current task at the end, to reduce reference-copying.
- Prompt 009 again reached its 3500-token output limit after 113.31 seconds. The incomplete service output was not applied. The stream repeated conditional blocks. New configuration experiment: temperature 0.3, repeat_penalty 1.15, repeat_last_n 256, num_ctx 8192, short per-operation prompts.

User clarified: retain model logic bugs; do not manufacture failures or improve logic to change results. Prompt 010 with reduced context/repetition settings completed in 11.42s; prompt 011 completed in 6.05s. These are generation timings, not evidence of functional correctness or general model efficiency.

Build checks: Django system check, Python compilation, no migration drift and isolated ELM migration all pass. Full temporary SQLite Fusion migration fails in existing Placement0009 with missing document_profile_idx after ELM0001 succeeds; preserved baseline files. Actual PostgreSQL connection and workflow functionality were not tested.

Prompts 024–026 returned truncated JSX inside syntactically valid JSON, with stop completion. Changed single-file frontend requests to raw source without JSON constraints. Exact original payloads/output retained; subsequent format/system changes logged in each request and prompts.md.
