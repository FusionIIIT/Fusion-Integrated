# Qwen3.5:9B ELM Trial

This directory contains the complete record of an exploratory code-generation trial using Qwen3.5:9B (NVFP4, MLX runner) to generate a Leave management module for Fusion ERP.

## Structure
- `prompts.md`: Prompt sequence and settings.
- `responses/`: Exact request payloads, streamed raw outputs, statistics and before-files (exported copies are redacted).
- `checks.log` / `checks.jsonl`: Execution logs and return codes.
- `jobs/`: Saved generation task plans; requests in responses/ establish which were actually executed.
- `trial-metadata.json`: Hardware and runtime configuration.
- `observed-results.json`: Summary of checks and outcomes.
- `mechanical-corrections.md`: List of manual fixes applied post-generation.
- `file-inventory.json`: File manifest.
- `final-model-differences.patch`: Diff from the last applied model content to the final mechanically integrated application source.

## Documentation Index
1. [Trial Record](./TRIAL_RECORD.md): Configuration, assessment table, and classification.
2. [Comparison](./COMPARISON.md): Two-model summary (Qwen3.5:9B vs Qwen2.5-Coder:3B).
3. [Module Docs](../../../modules/leave_elm/README.md): Generated module layout and known failures.
