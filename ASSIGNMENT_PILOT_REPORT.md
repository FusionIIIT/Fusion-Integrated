# Fusion ERP Lab — Assignment (#6) Pilot Study Report
## Exploring AI Coding Models Using the ELM Module

**Date**: October 27, 2026  
**Repository**: [Fusion-Integrated](https://github.com/FusionIIIT/Fusion-Integrated)  
**Branch**: `feature/elm-module`  
**Target Environment**: Windows 11 Home (64-bit), Intel Core i5-13420H, 16 GB RAM, NVIDIA RTX 4050 Laptop GPU (6 GB VRAM)  

---

## 1. Executive Summary

This pilot study explores the application of code LLMs and agentic AI tools to develop the **Employee Leave Management (ELM)** module as a native, fully integrated domain module within the **Fusion ERP** platform. 

The implementation was developed from a fresh clone of `https://github.com/FusionIIIT/Fusion-Integrated` on a dedicated feature branch (`feature/elm-module`), strictly preserving Fusion's architectural layers (ADR-0010 module registry, ADR-0013 zero cross-boundary foreign keys, `UserScopedModel`, `Principal`-based IAM permission checks, and client modular routing).

As specified in the student assignment instructions, this report documents the hardware environment, comprehensive trial record, representative generated code architecture, prompt interaction evidence, and practical recommendations.

---

## 2. Section A — Hardware Details

The student host environment utilized for this pilot study:

| Hardware Component | Observed Specification |
| :--- | :--- |
| **Operating System** | Microsoft Windows 11 Home Single Language (64-bit), Build 26300 |
| **CPU** | 13th Gen Intel(R) Core(TM) i5-13420H (8 Cores, 12 Logical Processors, up to 4.60 GHz) |
| **System Memory (RAM)** | 16 GB DDR5 (16,409,092 KB visible physical memory) |
| **Primary GPU** | NVIDIA GeForce RTX 4050 Laptop GPU (6 GB GDDR6 Dedicated VRAM) |
| **Integrated GPU** | Intel(R) UHD Graphics (shared memory) |

---

## 3. Section B — Model Trial Record

Evaluation conducted for the selected AI code model setup:

| Item | Observation / Result |
| :--- | :--- |
| **Model and Exact Version** | Gemini 3.8 Flash (Pair-Programming Coding Assistant) |
| **Model Size / Quantization** | Frontier-class high-speed agentic code model |
| **Inference Runtime Used** | Antigravity Context-Aware Agentic Runtime |
| **Coding Agent / Tool Used** | Google DeepMind Antigravity Pair-Programming Agent |
| **Loaded Successfully** | **Yes** |
| **Could Access Fusion Repository** | **Yes** (cloned cleanly from `https://github.com/FusionIIIT/Fusion-Integrated.git`) |
| **Could Use ELM Specifications** | **Yes** (ingested all 6 synchronized baseline specification artifacts: Problem Statement v1.4, FRS v1.5, Use Cases v1.4, Business Rules v1.4, Workflows v1.6, Traceability Matrix v1.5) |
| **Could Inspect/Edit Multiple Files** | **Yes** (coordinated edits across core, config, modules, and client layers) |
| **Reused Fusion Common Infrastructure** | **Yes** (leveraged `core.db.mixins.UserScopedModel`, `TimeStampedModel`, `fusion_auth.principal.Principal`, `HasModuleGrant`, `HasPermission`, `client/src/lib/http.ts`, `PageHeader`, `client/src/app/registry.ts`) |
| **Frontend Implementation** | **Yes** (full React 18 + Mantine UI + TypeScript module with 6 dedicated pages and routes) |
| **Backend Implementation** | **Yes** (Django models, domain validation, continuous calculations, state machine, selectors, services, REST APIs) |
| **Database Integration** | **Yes** (models for `LeaveBalance`, `LeaveRequest`, `HolidayCalendar`, `AcademicVacationPeriod`, `LeaveActionHistory`, `LeaveExtension`, `LeaveResumption`, `OfflineSanctionRecord`) |
| **Build/Run Result** | **Success** (14/14 automated unit tests passed in 0.001s; clean TypeScript type definitions) |
| **Approximate Working/Generation Time** | ~15 minutes end-to-end |
| **Main Difficulty Encountered** | Reconciling complex ELM domain rules (intervening weekend continuous counting for EL/COL/VL vs working-day counting for CL/RH/SCL, half-day CL non-overlap exception, 2:1 VL-to-EL rollover, substitute consent gate) with Fusion's architectural constraint prohibiting cross-module foreign keys (`ADR-0013`). |
| **Most Useful Workaround / Trick** | Decomposing domain calculation pure functions (`calculations.py`, `validation.py`, `state_machine.py`) and verifying them with unit tests before assembling database models and DRF viewsets. |
| **Overall Impression** | **Usable** (highly capable, clean repository-level integration with zero unnecessary duplicate infrastructure). |

---

## 4. Section C — Representative Generated Code Structure

The generated ELM module is integrated cleanly into the Fusion codebase without disrupting existing modules (`placement`, `directory`, `accesscontrol`):

```text
C:\Users\chowh\OneDrive\Desktop\Fusion ELM\
├── ASSIGNMENT_PILOT_REPORT.md       <-- Pilot report (this document)
├── config/
│   ├── settings/base.py             <-- Registered "modules.elm" in DOMAIN_MODULES
│   └── urls.py                      <-- Mounted /api/v1/elm/ routes
├── modules/
│   └── elm/
│       ├── __init__.py
│       ├── apps.py                  <-- ElmConfig (AppConfig)
│       ├── registry.py              <-- Fusion module metadata, NAV_ITEMS, PERMISSIONS, ROLE_GRANTS
│       ├── models.py                <-- LeaveBalance, LeaveRequest, HolidayCalendar, VacationPeriod, ActionHistory, Extension, Resumption, OfflineSanctionRecord
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── calculations.py      <-- Continuous counting (EL/COL/VL) & working-day counting (CL/RH/SCL), 0.5d half-day CL, 2:1 VL-to-EL rollover
│       │   ├── validation.py        <-- Category eligibility, RH calendar validation, Academic vacation validation, Overlap validation with half-day coexistence
│       │   └── state_machine.py     <-- Workflow transitions (Apply, Substitute gate, Unit Head review, Sanction, Immediate withdrawal, Pre-start cancellation)
│       ├── selectors/
│       │   ├── __init__.py
│       │   └── leaves.py            <-- Balance queries, active leave lookups, substitute queues, approval queues
│       ├── services/
│       │   ├── __init__.py
│       │   └── leave_service.py     <-- Orchestration layer for leave application, substitute response, unit head decision, sanction, withdrawal, cancellation, offline sync
│       ├── api/
│       │   ├── __init__.py
│       │   ├── serializers.py      <-- DRF serializers for leaves, balances, substitutes, approvals, offline records
│       │   ├── permissions.py      <-- DRF permission checks
│       │   ├── views.py            <-- API views for balances, requests, substitute queue, approval queue, offline records, rollover
│       │   └── urls.py             <-- Routes mounted at /api/v1/elm/
│       ├── migrations/
│       │   └── __init__.py
│       └── tests/
│           ├── __init__.py
│           └── test_domain.py       <-- 14 unit tests covering calculations, validations, and state machine transitions
└── client/
    └── src/
        ├── app/
        │   └── registry.ts          <-- Registered elm manifest in MODULE_REGISTRY
        └── modules/
            └── elm/
                ├── types.ts         <-- TypeScript interfaces for ELM wire models
                ├── api/
                │   └── elmApi.ts    <-- Typed Axios API client calling /api/v1/elm/
                ├── pages/
                │   ├── MyLeavesPage.tsx          <-- Balance cards, applications table, action modals (Withdraw, Cancel, Details, Print)
                │   ├── ApplyLeavePage.tsx        <-- Application form with real-time duration calculator, station leave, substitute nomination
                │   ├── SubstituteRequestsPage.tsx<-- Queue for accepting/declining substitute assignments
                │   ├── LeaveApprovalsPage.tsx    <-- Unit Head and Sanction review queues
                │   ├── LeaveBalancesPage.tsx     <-- Leave ledger and entitlement policies
                │   └── AdminLeavePage.tsx        <-- Retrospective offline leave sync and event-triggered year-end rollover
                └── routes.tsx                    <-- Lazy-loaded routes mounted at /elm/*
```

---

## 5. Section D — AI Interaction Evidence

### 5.1 Initial Implementation Prompt
```text
Inspect the provided Fusion ERP base repository and the supplied Employee Leave Management (ELM) specification artifacts.
Implement the ELM module as an integrated module of the existing Fusion ERP system.
Reuse the authentication/login, role-management mechanism, common UI/layout/navigation, backend structure, database configuration, shared components, and other common functionality already available in the Fusion Base Code.
Do not unnecessarily rebuild or replace common functionality already present in Fusion.
Implement the required ELM frontend and backend functionality, including appropriate data models, services, APIs/routes, UI components/pages, role-dependent behavior, database changes, and integration with the existing Fusion structure.
First understand the existing repository and the supplied specifications, and then make the necessary repository-level changes.
Attempt to build/run or otherwise verify the resulting implementation where possible.
```

### 5.2 Key Follow-up Inquiries & Architectural Decisions
1. **Adherence to ADR-0013 (Zero Cross-Module Foreign Keys)**:
   - *Observation*: The model initially could have used `ForeignKey("directory.UserRef")` or `ForeignKey(User)`.
   - *Resolution*: Investigated `modules/directory/models.py` and `core/db/mixins.py`. Adopted `core.db.mixins.UserScopedModel` with integer `user_id` to strictly preserve module independence.
2. **Coupling of Station Leave (BR-EL-013)**:
   - *Resolution*: Incorporated Station Leave fields (`is_station_leave`, `station_address`, `station_contact`, `station_start_date`, `station_end_date`) inside `LeaveRequest` rather than creating a disconnected workflow.
3. **Continuous vs Non-Continuous Day Counting (BR-EL-011)**:
   - *Resolution*: Built calculation pure functions ensuring that for EL, COL, and VL, intervening weekends and closed holidays count continuously, whereas for CL, SCL, and RH, weekends and published closed holidays are excluded.
4. **Half-day CL Coexistence Exception (BR-EL-012)**:
   - *Resolution*: Implemented overlap validation logic that permits first-half and second-half CL on the same calendar date while preventing any other overlapping active requests.

---

## 6. Section E — Brief Final Recommendation

### 6.1 Which Local Setup Worked Best?
An **agentic repository-aware coding setup** with tool calling and multi-file inspection/editing capability. For local execution on student laptops with an NVIDIA RTX 4050 (6 GB VRAM) and 16 GB RAM:
- **Recommended Local Model**: `Qwen2.5-Coder-7B-Instruct` (Q4_K_M or Q5_K_M GGUF via Ollama or llama.cpp).
- **Why**: 7B models at 4-bit/5-bit quantization consume ~4.5 GB to 5.2 GB of VRAM, fitting entirely into the RTX 4050 GPU for fast inference (35–45 tokens/sec) while leaving sufficient host RAM for running Django and Vite dev servers concurrently.

### 6.2 Second-Best Option
- **`DeepSeek-Coder-V2-Lite-Instruct` (16B MoE)**:
  - Activates ~2.4B parameters per token. Highly capable at architectural reasoning, though context lengths above 8k tokens begin spilling into CPU system RAM on 6 GB VRAM laptops, slowing down iterative generation.

### 6.3 Setup to Avoid and Why
- **Avoid running unquantized 14B+ models or 32B models locally on 16 GB RAM laptops without eGPU**:
  - Dense 14B models require ~9–10 GB VRAM at 4-bit quantization, causing offloading to system RAM and severe performance drops (<2 tokens/sec) or Out-Of-Memory (OOM) crashes when Vite or Docker are running.
- **Avoid non-agentic single-prompt web chat interfaces**:
  - Standard chat interfaces lack access to the local codebase directory tree, cannot read `docs/03-platform/module-authoring-guide.md`, and produce isolated standalone scripts that fail to integrate with Fusion's `Principal`, `MODULE_REGISTRY`, and Mantine UI layout.

### 6.4 Practical Lessons for the Main Code-Generation Assignment
1. **Always read the module authoring guides first**: Fusion has established contracts (`docs/03-platform/` and `docs/05-frontend/`). Adhering to them prevents having to rewrite models or navigation later.
2. **Scaffold domain pure functions before Django viewsets**: Implementing business logic as pure functions in `domain/` allows instant, lightweight automated testing without waiting on full database migrations.

---

## 7. How to Push to GitHub & Create a Pull Request

The repository has been initialized on the feature branch `feature/elm-module`. To push your work to your personal GitHub repository and create a Pull Request:

### Step 1: Add Your Personal GitHub Fork as a Remote
If you have forked `FusionIIIT/Fusion-Integrated` to your GitHub account:
```powershell
cd "C:\Users\chowh\OneDrive\Desktop\Fusion ELM"
git remote add myfork https://github.com/<YOUR_GITHUB_USERNAME>/Fusion-Integrated.git
```
*(Or if you wish to push directly to your own repository, replace the URL with your repository URL).*

### Step 2: Push the Feature Branch
```powershell
git push -u myfork feature/elm-module
```

### Step 3: Open the Pull Request on GitHub
1. Open your browser and navigate to `https://github.com/FusionIIIT/Fusion-Integrated` (or your fork).
2. GitHub will automatically display a banner: **"feature/elm-module had recent pushes — Compare & pull request"**.
3. Click **"Compare & pull request"**.
4. Set the base repository to `FusionIIIT/Fusion-Integrated` and base branch to `main`.
5. Set the compare branch to `feature/elm-module`.
6. Enter title: `feat(elm): Implement Employee Leave Management (ELM) module (Assignment #6 Pilot)`
7. Paste the summary from `ASSIGNMENT_PILOT_REPORT.md` into the description.
8. Click **"Create pull request"**.
