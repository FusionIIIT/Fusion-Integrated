# Assignment 7 (LMS Course Management) - AI Interaction & Prompt Log

## 1. Environment & Setup Details
- **Operating System**: Windows 10 Pro (64-bit, Build 19045)
- **CPU**: Intel(R) Core(TM) i3-5010U @ 2.10GHz (2 Cores, 4 Logical Processors)
- **RAM**: 4,017 MB (~4 GB)
- **GPU / VRAM**: Intel(R) HD Graphics 5500 (Integrated, ~1 GB shared VRAM, CPU-only inference)
- **Model Name & Version**: `qwen2.5-coder:1.5b-instruct`
- **Family**: Qwen 2.5 Coder
- **Parameter Size**: 1.5 Billion parameters
- **Quantization**: `Q4_K_M` (~1.1 GB download)
- **Inference Runtime**: Ollama (local CLI / API server v0.35.1)
- **Coding Tool / Agent**: Antigravity IDE / VS Code

---

## 2. Interaction Session & Prompts

### Phase 1 Initial Implementation Request (Prompt 1)
```text
Inspect the provided Fusion ERP base repository and the supplied LMS (Course Management) specification artifacts (01_LMS_CourseManagement_Problem_Statement_v1.0_UNCHANGED.docx, Use Cases, Business Rules, and Workflows).
Implement the LMS module as an integrated module of the existing Fusion ERP system.
Reuse the authentication/login, role-management mechanism, common UI/layout/navigation, backend structure, database configuration, shared components, and other common functionality already available in the Fusion Base Code.
Do not unnecessarily rebuild or replace common functionality already present in Fusion.
Implement the required LMS frontend and backend functionality, including appropriate data models, services, APIs/routes, UI components/pages, role-dependent behavior, database changes, and integration with the existing Fusion structure.
First understand the existing repository and the supplied specifications, and then make the necessary repository-level changes.
Attempt to build/run or otherwise verify the resulting implementation where possible.
```

#### Model Response & Observations (Trial 1 — `qwen2.5-coder:1.5b`):
- **Generation Speed**: ~14 tokens/sec on Intel Core i3 CPU.
- **Context Handling**: Successfully parsed the core problem statement, but due to 4GB RAM limits, context window truncated when attempting to process entire Fusion monolithic repository at once.
- **Output Produced**: Generated initial database models for `CourseWorkspace`, `CourseMembership`, `CourseMaterial`, `CourseAnnouncement`, `Assignment`, `StudentSubmission`, `Grade`, and `GradeChangeLog` in `modules/lms/models.py`.
- **Defects & Failures Identified**:
  - Failed to register the Django app in `config/settings/base.py` (`DOMAIN_MODULES`).
  - Did not generate `registry.py` or permission grants for the RBAC permission manifest.
  - Missed cross-module ADR guidelines initially (attempted direct `ForeignKey` to non-existent auth User table before correction to plain `user_id = models.IntegerField(db_index=True)`).
  - Failed to generate frontend pages or REST API views across files due to multi-file coordination limits.

---

### Follow-Up Request 1 (Prompt 2 — Schema Refinement & ADR Compliance)
```text
Focus on the backend data schema for LMS Course Management according to BR-LMS-001 through BR-LMS-019.
We need tables for CourseWorkspace, CourseMembership, CourseMaterial, CourseAnnouncement, Assignment, StudentSubmission, Grade, and GradeChangeLog.
Ensure foreign keys to User are decoupled as plain user_id integers per Fusion ADR-0013.
Inherit from TimeStampedModel.
```

#### Model Response:
- Refined `modules/lms/models.py` by converting cross-module references to plain `user_id` integers with `db_index=True`.
- Added state fields: `status` on `CourseMaterial` (`draft`, `scheduled`, `published`), `Assignment` (`draft`, `scheduled`, `available`), `StudentSubmission` (`submitted`, `late`, `missing`), and `Grade` (`draft`, `released`).
- Included `GradeChangeLog` for post-release audit trails.

---

### Follow-Up Request 2 (Prompt 3 — Frontend & Service Layer Generation Attempt)
```text
Generate the React frontend components for the LMS module in client/src/modules/lms using Mantine and React Router, along with the DRF API endpoints and service layer.
```

#### Model Response:
- Due to the small parameter size (1.5B), the model produced a single hallucinated stub file with syntax errors and missing Mantine 7 imports.
- Demonstrated that local small models on low-spec hardware require human-in-the-loop architectural scaffolding for complex multi-file frontend and service-layer stacks.

---

## 3. Alternative Trial Comparison (`qwen2.5-coder:0.5b`)
- **Parameters**: 0.5B (Q4_K_M, ~350 MB).
- **Outcome**: Fast generation (~28 tokens/sec), but produced severe hallucinations, basic syntax errors (`class CourseWorkspace(models.def)`), failed indentations, and could not respect Fusion Base patterns.
- **Selection Decision**: Selected `qwen2.5-coder:1.5b` as the superior baseline for Phase 1 code generation, paired with human-in-the-loop decomposition for Phase 2 production engineering.

---

## 4. Phase 2 Human-in-the-Loop Engineering
In Phase 2, the human-in-the-loop intervention expanded the 1.5B baseline into full production deployment readiness:
1. **Domain Isolation**: Pure domain entities (`domain/entities.py`), errors (`domain/errors.py`), business rules `BR-LMS-001` through `019` (`domain/rules.py`), and state machine transitions `CW-LMS-01`, `CW-LMS-02` (`domain/state_machine.py`).
2. **Selectors & Atomic Services**: Read-only query encapsulation (`selectors/courses.py`) and transactional mutation services with audit logging (`services/courses.py`).
3. **DRF API & RBAC Security**: DRF viewsets and views (`api/views.py`) enforced with `fusion_auth` permission classes (`api/permissions.py`) and serializers (`api/serializers.py`).
4. **Platform Wiring**: Registered `modules.lms` in `DOMAIN_MODULES`, mounted routes at `api/v1/lms/`, and generated permission catalog entries in `registry/permissions.json`.
5. **Modern Mantine React UI**: Fully decoupled SPA in `client/src/modules/lms/` containing `CourseListPage`, `CourseWorkspacePage`, `AssignmentDetailPage`, `GradingPage`, hooks, types, and route manifest.
6. **Verification**: 24 automated domain unit tests passing (100%), 0 Django check issues, and TypeScript/Vite production build passing cleanly.
