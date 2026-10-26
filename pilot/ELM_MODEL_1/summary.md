# Trial 1 — Local AI Coding Model Summary

## 1. Environment & Model Configuration
- **Machine**: Apple MacBook Air (M3, 8-Core CPU, 10-Core GPU, 16 GB Unified Memory)
- **OS**: macOS (Darwin)
- **Model**: `qwen2.5-coder:7b` (7.6B parameters)
- **Quantization**: `Q4_K_M` (4.7 GB)
- **Inference Runtime**: Ollama
- **Coding Agent**: Continue VS Code Extension (`32K` context window)

## 2. Step-by-Step Implementation Log
| Step | Description | Outcome |
|---|---|---|
| Step 1 | Module foundation (`apps.py`, `registry.py`) | Created module metadata and navigation definitions |
| Step 2 | Initial Django ORM models (`models.py`) | Generated `LeaveType`, `LeaveBalance`, `LeaveApplication`, `SubstituteNomination` |
| Step 3 | Domain policy (`domain/policy.py`) | Defined pure-Python leave codes (`CL`, `RH`, `SCL`, `EL`, `VL`, `COL`) and annual entitlements |
| Step 4 | Application services (`services/applications.py`) | Added leave submission, substitute nomination, and withdrawal services |
| Step 5 | REST API (`api/serializers.py`, `views.py`, `urls.py`) | Created DRF views and serializers guarded by `HasModuleGrant` and `HasPermission` |
| Step 6 | Module & route registration (`settings/base.py`, `urls.py`) | Initial model edit in `config/urls.py` introduced `core.api.elm_module` |
| Step 7 | Database migration (`migrations/0001_initial.py`) | Initial schema migration for the 4 ELM tables |
| Step 8 | Frontend wiring (`registry.ts`, `api.ts`, `routes.tsx`) | Registered `/elm` module and client route definitions |
| Step 9 | Frontend pages (`LeaveBalance.tsx`, `LeaveApplication.tsx`) | Generated React components for viewing balance and submitting applications |
| Step 10 | Mechanical integration pass | Replaced `ForeignKey(User)` with integer user IDs, adapted `RouteObject[]` export, and synced `registry/permissions.json` |

## 3. Key Empirical Findings
1. **Binary Specification Files**: Supplying raw `.docx` files directly caused the agent to read the underlying ZIP/XML structure (`word/document.xml`). Converting the specifications to Markdown (`.md`) resolved this and allowed accurate extraction of the 6 leave categories and status lifecycles.
2. **Agent Tool-Calling vs. Chat Mode**: In Continue's Agent mode, `qwen2.5-coder:7b` frequently emitted raw JSON tool-call text (`{"name": "ls"}`, `{"name": "read_file"}`, `{"name": "single_find_and_replace"}`) instead of executing edits smoothly. Switching to Chat mode with `@currentFile` context produced clean code blocks that could be applied per file.
3. **Mechanical Integration Needs**: The raw LLM output assumed standard Django `auth.User` foreign keys and default React Router `<Routes>` exports, requiring mechanical adjustments to match Fusion-Integrated's IAM `user_id` convention and `RouteObject[]` module manifest contract.
