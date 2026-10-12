# Qwen 3.5 9B ELM trial

Independent clean worktree from official latest main 02b01fea4a67b257ea7000009f06a1561699550e, identical to the first trial base. No first-model ELM application output was copied. Shared trial harness, specification extracts and initial task plans were reused.

The installed model supports thinking; requests explicitly set think=false to generate code without a separate thinking phase. Actual per-call settings and outputs will be recorded. Build/integration checks only; workflow bugs are to remain. This is an exploratory comparison, not a controlled performance benchmark.

During prompt001, ollama ps reported qwen3.5:9b using 7.7 GB, 100% GPU, context4096 and runnermlx despite requested num_ctx32768. Requested settings do not by themselves establish the runtime context actually used. This discrepancy is preserved rather than assuming identical effective settings across models.

Comparison limits: stage instructions and specification inputs are reused, but this trial uses the final evolved harness (references before CURRENT TASK), while early first-trial prompts used the older ordering. Model/runtime/quantization and thinking capability differ. This is the same implementation exercise, not byte-identical prompting or a controlled model-efficiency benchmark.

For API generation, removed repeated specification text from input because this stage wraps existing generated service/model interfaces, without changing their logic. Full specifications were provided to foundation/service stages. API request uses shorter interface-only context and requested context16384; exact payload will be logged.

Frontend interface generation uses requested context16384 and temperature0.2, with exact options saved in each request. First-model build/timing summary copied for later comparison only; its ELM application source was not used as second-model input.

Backend Django checks, syntax compilation, isolated schema/module seeding, import boundaries, migration drift, task imports and API schema generation passed. API schema emitted one operation-ID collision warning. Full temporary SQLite migration failed in baseline Placement0009. The repository permission-manifest registration command failed validation; its full output is retained in checks.log. No permission enforcement or application behavior was changed to pass that gate, in accordance with the mechanical-correction-only scope. This is partial integration success, not a claim that every repository gate passes.

Final frontend strict TypeScript and production build passed after documented mechanical interface corrections. Remaining build warnings were retained without optimization. Navigation route registration passed. Application generation used eleven recorded requests, totaling2504.01 seconds of aggregate request wall time (about41.7 minutes), excluding documentation requests and supervision/build time. Original checkout remains separate from codex/elm-qwen35-9b.
