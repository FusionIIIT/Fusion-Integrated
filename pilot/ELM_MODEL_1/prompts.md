# Trial 1 - Prompts & Interaction Log (Qwen2.5-Coder:7b + Continue)

## Student Information
- **Roll Number**: 24BCS170
- **Partner Roll Number**: 24BCS182
- **Model**: `Qwen2.5-Coder:7b` (via Ollama / Continue IDE extension)

---

## Prompt 1 - Repository Inspection
```text
@codebase What existing modules are present under the modules/ directory in this repository, and what frameworks are used for the backend and frontend?
```
- **Observation**: In Agent mode, the model emitted `{"name": "ls", "arguments": {"dirPath": "modules/", "recursive": false}}`. Switched to Chat mode to inspect repository files directly.

## Prompt 2 - Specification Ingestion
```text
@currentFile According to this specification document, what are the 6 leave categories supported by ELM, what are their annual entitlements, and what is the rule for unused VL at year end?
```
- **Observation**: When bound to the raw `.docx` file, the model reported seeing a ZIP directory listing (`word/document.xml`). After converting `01_ELM_Problem_Statement_v1.4_FINAL.docx` to `.md`, the model accurately identified `CL` (8 days), `RH` (2 days), `SCL` (15 days), `EL` (30 days), `VL` (60 days, 2:1 conversion to EL), and `COL` (20 days).

## Prompt 3 - Backend URL Registration
```text
Add the route for the ELM module right below this line following the same pattern
```
- **Observation**: Model inserted `path("api/v1/elm", elm_module)` along with hallucinated imports `from core.api.router import router` and `from core.api.elm_module import elm_module`. Repaired in the mechanical integration pass to `path("api/v1/elm/", include("modules.elm.api.urls"))`.

## Prompt 4 - Database Models Generation
```text
@file specs/01_ELM_Problem_Statement_v1.4_FINAL.md Based on these ELM specifications, generate the Django database models (models.py) for the ELM module.
Include:
1. LeaveBalance model for each employee tracking the 6 leave types (CL, RH, SCL, EL, VL, COL).
2. LeaveApplication model with applicant, leave type, start/end date, station leave details, and statuses (PENDING, APPROVED, REJECTED, WITHDRAWN, CANCELLED).
3. SubstituteNomination model for responsibility coverage.
Link them appropriately to the Django User/Employee model.
```
- **Observation**: Generated `LeaveType`, `LeaveBalance`, `LeaveApplication`, and `SubstituteNomination` models. Mechanically adapted `ForeignKey(User)` to integer IDs (`employee_id`, `applicant_id`, `substitute_id`) to comply with Fusion's no-cross-module-FK architecture.

## Prompt 5 - Frontend Module Generation
```text
@currentFile Using this placement routes.tsx as a structural reference, write the React frontend code for the new ELM module under client/src/modules/elm/.
Include:
1. routes.tsx with routes for leave balance and leave application.
2. A React component with a form to apply for leave (CL, RH, SCL, EL, VL, COL).
```
- **Observation**: Generated `routes.tsx`, `LeaveBalance.tsx`, and `LeaveApplication.tsx` with form controls for all 6 leave types. Adapted `routes.tsx` export to `export const routes: RouteObject[]` in the mechanical pass.
