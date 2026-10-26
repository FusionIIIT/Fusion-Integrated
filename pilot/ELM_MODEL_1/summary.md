# ELM Model 1 Trial Summary: `qwen2.5-coder:14b` (Ollama + Continue)

## Trial Overview
- **Model**: `qwen2.5-coder:14b` (Ollama library tag `qwen2.5-coder:14b`)
- **Quantization**: `Q4_K_M` (~9.0 GB VRAM requirement)
- **Runtime**: Ollama, Metal GPU acceleration
- **Interface**: Continue extension in VS Code
- **Context Window**: 32K (`32768` tokens)
- **Base Commit**: `02b01fe` (clean main base)

## Execution Findings
1. **Spec Handling**: Supplying raw `.docx` files caused Continue to parse binary ZIP headers. Converting `.docx` to Markdown slices and feeding layer-specific sections worked smoothly.
2. **Model Capacity & Quality**: Compared to the 7B variant, `qwen2.5-coder:14b` generated much more consistent domain logic and cleaner serializers with fewer type mismatches.
3. **Hardware / Resource Impact**: The 14B model required ~9 GB of GPU memory, resulting in noticeably slower generation speeds (~14 tok/s vs ~32 tok/s on 7B) but significantly improved semantic cohesion across layer files.
4. **Mechanical Corrections (Step 10)**: 
   - Replaced Django `ForeignKey(User)` with integer `user_id` fields to adhere to Fusion IAM boundaries.
   - Fixed `include("modules.elm.urls")` to `include("modules.elm.api.urls")`.
   - Adapted React router export to `export const routes: RouteObject[]`.
   - Updated `.importlinter` boundaries and synced `registry/permissions.json`.
