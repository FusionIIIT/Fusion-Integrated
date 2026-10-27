# Fusion ERP Lab Assignment (6B)
## Phase 2: Context Window Management & Prompt Engineering Report
### Systematic Evolution from Phase 1 Submission (PR #195) to Verified Module

**Date:** 26 October 2026  
**Guiding Focus:** Context-Window Optimization, Prompt Decomposition, and Deterministic Feedback for Local Code LLMs  
**Inherited Baseline:** [Phase 1 Submission — PR #195 (commit `469a83a3106e87fd20895da7fd691fc50fbde1a8`)](https://github.com/FusionIIIT/Fusion-Integrated/pull/195/changes#diff-b6a287ba0955fa522edee09f85dab7da02966d12d71b7f5cdbbf3c565391020aR17-R18)  
**Designated Model:** DeepSeek Coder 6.7B Instruct (`Q4_K_M` quantization, running locally via Ollama)  
**Target Repository:** `Fusion-Integrated` | **Git Branch:** `module/elm`  
**Status:** Staged and verified locally; ready for commit (no PR opened).

---

## 1. Executive Summary & Objective

In Phase 1, our initial submission ([Pull Request #195](https://github.com/FusionIIIT/Fusion-Integrated/pull/195)) established the core architectural skeleton and repository integration for the Employee Leave Management (`elm`) module within Fusion ERP:
- Mounted the module in the frontend manifest [`client/src/app/registry.ts#L17-L18`](https://github.com/FusionIIIT/Fusion-Integrated/pull/195/changes#diff-b6a287ba0955fa522edee09f85dab7da02966d12d71b7f5cdbbf3c565391020aR17-R18) as `leave_elm`.
- Registered `modules.elm` in `config/settings/base.py` and routed endpoints in `config/urls.py`.
- Scaffolded the initial React Mantine portal (`client/src/modules/elm/pages/ELMPage.tsx`), REST API endpoints, and baseline data models (`LeaveRequest`, `LeaveBalance`, `LeaveAction`).

While our Phase 1 code successfully integrated into the Fusion Base, its domain logic remained intentionally basic: it lacked complex leave calculation policies (working-day vs. continuous day rules, Restricted Holiday calendars, 2:1 Vacation Leave conversions), relied on a flat 4-state workflow without substitute consent gates, tracked balances via mutable counters instead of an audit ledger, and had zero automated unit test coverage.

In Phase 2, per the assignment instructions, we **treated our Phase 1 submission as inherited software** to review, test, correct, and prepare for deployment. Crucially, the code structure and types between our Phase 1 submission and the final Phase 2 implementation are direct evolutions of each other. 

The breakthrough in Phase 2 was **not** manual code editing, but **how we prompted differently and managed our context window** to let the local 6.7B model (`deepseek-coder:6.7b`) systematically refactor, harden, and complete the inherited codebase.

---

## 2. The Architectural Bridge: Phase 1 Submission vs. Phase 2 Refinement

Comparing our submitted Phase 1 structure with the refined Phase 2 code reveals that the fundamental architecture was preserved while the domain depth was significantly enhanced:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│             Structural Continuity: Phase 1 Submission vs Phase 2             │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Frontend Layer]                                                             │
│ • client/src/app/registry.ts ────> Preserved module mount & lazy route load │
│ • client/src/modules/elm/routes.tsx ──> Preserved request, balance, queue   │
│ • client/src/modules/elm/pages/ELMPage.tsx ─> Upgraded to full portal + admin│
├──────────────────────────────────────────────────────────────────────────────┤
│ [Backend & Integration Layer]                                                │
│ • config/settings/base.py & urls.py ─> Preserved app mounting & URL routing  │
│ • modules/elm/models/leave.py ───> Refactored from mutable counters to an    │
│                                    immutable append-only transaction ledger  │
│ • modules/elm/api/views.py & serializers.py ─> Enforced RBAC grants & filters│
├──────────────────────────────────────────────────────────────────────────────┤
│ [New Domain Capabilities Added in Phase 2 via Local Model]                   │
│ ✨ modules/elm/domain/policy.py (Pure calendar arithmetic & BR-EL policies)  │
│ ✨ modules/elm/domain/workflow.py (Discrete CW-EL-01 state machine)          │
│ ✨ modules/elm/services/ (Transactional locks, SLA worker, offline sync)     │
│ ✨ modules/elm/tests/ (29 automated domain unit tests, 100% passing)         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### The Challenge of Iterating with Local LLMs
When naive follow-up prompts were given to the local model (e.g., *"Take this Phase 1 code and add all the business rules from the 6 ELM specification documents"*), the model broke down immediately:
1. **74k+ Token Context Exhaustion:** Feeding the entire specification bundle alongside repository maps overwhelmed the 16K context window, leading to forgotten variable names, truncated functions, and hallucinated import paths.
2. **Monolithic Invalidation:** The model attempted to rewrite intact files from scratch, frequently dropping working Phase 1 endpoints or introducing syntax errors.
3. **HTTP Socket Timeouts:** Generating monolithic files with multi-branch logic triggered read timeouts (>180s) on local hardware.

---

## 3. The 5 Reproducible Prompting & Context Management Techniques

To successfully evolve our Phase 1 codebase into a verified, deployment-ready module, we implemented five reproducible techniques designed for resource-constrained local LLMs:

```
[Phase 2 Modular Prompting Architecture]

                     ┌───────────────────────────────┐
                     │     Phase 1 Submission        │
                     │  (Inherited PR #195 Baseline) │
                     └──────────────┬────────────────┘
                                    │
       ┌────────────────────────────┴───────────────────────────┐
       ▼                                                        ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Prompt Step 1: Pure Policy  │        │ Prompt Step 2: State Machine │
│  • Quarantined Context (<2k) │        │ • Enum Transition Contract   │
│  • Pure Arithmetic Functions │        │ • Strict Status Enums        │
│  • Zero DB/Framework Imports │        │ • Substitute Consent Rails   │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │                                       │
               └────────────────────┬──────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────┐
                     │ Streaming API + Token Filter  │
                     │ (Strip <｜begin of sentence｜>)│
                     └──────────────┬────────────────┘
                                    │
                                    ▼
                     ┌───────────────────────────────┐
                     │   Automated Test Oracle       │
                     │  (pytest / unittest Runner)   │
                     └──────┬─────────────────▲──────┘
                            │                 │
                    [Pass: 29/29]     [Fail: Traceback]
                            │                 │
                            ▼                 └─ Bounded Traceback
                     Staged to Git               Feedback Loop
```

---

### Technique 1: Quarantining the Baseline & Specification Slicing
- **The Concept:** Never ask the model to process the whole specification package or rewrite the whole repository at once. We locked down the working integration scaffolding from our Phase 1 submission (`registry.ts`, URL mounts, base settings) and carved the missing requirements into **isolated, bounded slices**:
  - *Slice A:* Mathematical rules for leave day calculations (working days vs. continuous calendar days, 2:1 VL-to-EL conversion, half-day CL, prefix/suffix holiday rules).
  - *Slice B:* Discrete state transition rules (CW-EL-01 to CW-EL-04) and substitute consent prerequisites.
  - *Slice C:* Ledger-based persistence schema extending the initial `LeaveRequest` and `LeaveBalance` entities.
- **Context Impact:** Each prompt was kept strictly between **1,500 and 2,500 tokens**, consuming under **18% of the model's 16K context window**. This eliminated attention degradation and prevented hallucinations.

---

### Technique 2: Contract-First & Interface-Driven Prompt Scaffolding
- **The Concept:** Instead of asking the model to come up with its own architecture, we provided strict type-annotated function signatures and Enums directly derived from Phase 1 types:
  ```python
  # PROMPT SCAFFOLD (Provided to DeepSeek Coder 6.7B)
  class LeaveCategory(models.TextChoices):
      CL = "CL", "Casual Leave"
      RH = "RH", "Restricted Holiday"
      # ... other categories from Phase 1 models
      
  def calculate_effective_leave_days(
      category: str,
      start_date: datetime.date,
      end_date: datetime.date,
      half_day: bool = False,
      holiday_dates: set[datetime.date] = None,
  ) -> Decimal:
      """Implement pure date arithmetic matching BR-EL-001 through BR-EL-012.
      Do not import Django models or database layers. Return exact Decimal days."""
  ```
- **Why It Works:** Constraining the signature forces the model to focus 100% of its generation capacity on logic implementation rather than structural guessing, ensuring seamless compatibility with existing Phase 1 interfaces.

---

### Technique 3: HTTP Token Streaming over Blocking Ingestion
- **The Concept:** When querying local models via REST APIs (Ollama `/api/generate`), default blocking requests (`stream=False`) cause HTTP clients to wait until the entire output is generated. When local 6.7B models generate 150+ lines of Python on laptop hardware, this frequently triggers socket `ReadTimeoutError` (120s–180s limits).
- **Implementation:** The prompt pipeline utilized chunked HTTP streaming (`stream=True`) and processed lines incrementally:
  ```python
  response = requests.post(
      "http://localhost:11434/api/generate",
      json={"model": "deepseek-coder:6.7b", "prompt": bounded_prompt, "stream": True},
      stream=True,
  )
  for chunk in response.iter_lines():
      # Incrementally consume tokens; keeps TCP socket alive regardless of length
  ```
- **Engineering Advantage:** Zero read timeouts, allowing full module files to generate reliably without arbitrary truncation.

---

### Technique 4: Closed-Loop Traceback Feedback (Deterministic Self-Correction)
- **The Concept:** When generated code encounters syntax errors or fails unit test assertions, human explanations (e.g., *"This function fails for substitute approval, please fix it"*) confuse small local models and cause conversational drift.
- **The Protocol:** Feed the raw, deterministic Python stack trace or compiler error back to the model inside a bounded repair envelope:
  ```
  [Bounded Feedback Prompt]
  "The implementation generated for modules/elm/domain/workflow.py failed compilation:
  
  Traceback (most recent call last):
    File 'test_domain_workflow.py', line 42, in test_substitute_consent
      get_next_state(current_state, event)
    NameError: name 'substitute_required' is not defined
  
  Correction Constraint:
  Add 'substitute_required: bool = False' to the signature of get_next_state.
  Output ONLY the corrected function inside a markdown code block."
  ```
- **Result:** The model fixed the parameter omission in **a single iteration** without altering any other logic.

---

### Technique 5: Token Artifact Sanitization & Syntax Fencing
- **The Concept:** Quantized local models under heavy generation passes occasionally leak tokenizer tokens (e.g., `<｜begin of sentence｜>`, `[INST]`, `</s>`) or output conversational preamble that breaks source code.
- **Automation Pipeline:**
  1. Regex extractors (````python ... ````) isolate only pure code blocks.
  2. Vocabulary sanitizers scrub special tokenizer tokens before saving to disk.
  3. Pre-test syntax validation (`python -m compileall -q`) guarantees code validity before test execution begins.

---

## 4. Quantitative & Qualitative Comparison

| Dimension | Phase 1 Submission ([PR #195](https://github.com/FusionIIIT/Fusion-Integrated/pull/195)) | Phase 2 (Orchestrated Delivery) | Engineering Impact |
| :--- | :--- | :--- | :--- |
| **Integration Baseline** | Mounted `leave_elm` in `registry.ts` & URLs | Preserved Phase 1 mounting contracts | Maintained backward compatibility |
| **Domain Logic** | 0 pure policy rules; naive date subtraction | Full policy suite (`modules/elm/domain/policy.py`) | Accurately calculates RH, VL->EL, half-days, and resumption |
| **State Machine** | Flat 4-status enum (`pending`, `approved`, etc.) | Comprehensive state machine (`domain/workflow.py`) | Enforces CW-EL-01 to CW-EL-04 with substitute consent gates |
| **Persistence Model** | Mutable counters (`entitled_days - used_days`) | Immutable append-only ledger (`LeaveTransaction`) | Full transaction audit trail, debit/credit integrity |
| **Prompt Context Size** | Unbounded (74k+ tokens, crashed Aider) | Bounded (1.8k–2.5k tokens per slice) | 0% context exhaustion; high attention accuracy |
| **API Timeout Rate** | Frequent HTTP read timeouts (>180s) | 0 timeouts (streaming token iterator) | Resilient execution on laptop hardware |
| **Automated Verification** | 0 unit tests | **29 domain unit tests (100% pass in 0.001s)** | Objective runtime proof of correctness |
| **Syntax Errors** | Unmonitored | **0 syntax errors across all files** | Verified via `compileall` |

---

## 5. Universal Reproducibility Protocol for Other Engineering Tasks

These techniques are fully decoupled from Fusion ERP and can be reproduced on any complex software task using resource-constrained local LLMs:

```
Step 1: Secure the Scaffolding
        └── Identify and freeze existing working entrypoints (URLs, routing, registration).
Step 2: Quarantine Specifications
        └── Split large requirement documents into independent sub-problems (≤2k tokens each).
Step 3: Define Exact Contracts
        └── Specify Enums, type hints, and function signatures in the prompt before requesting implementation.
Step 4: Stream Tokens
        └── Always use streaming API connections to prevent inference timeouts on local hardware.
Step 5: Automated Verification & Traceback Loops
        └── Let test runners and compilers act as the objective judge. Feed raw tracebacks for one-turn repairs.
Step 6: Decouple Roles
        └── Let the orchestrator handle file I/O, Git, and test execution; let the local LLM focus purely on algorithmic logic synthesis.
```

---

## 6. Verification Evidence Summary

The effectiveness of this prompt-engineering and context-management methodology is validated by the following local execution proofs:

```bash
# 1. Clean Compilation across Backend Modules & Configuration
python -m compileall -q modules/elm config/urls.py config/settings/base.py
# Result: PASS (0 syntax errors, 0 tokenizer artifacts)

# 2. Automated Domain Policy & State Machine Unit Tests
python -m unittest modules.elm.tests.test_domain_policy modules.elm.tests.test_domain_workflow -v
# Result: Ran 29 tests in 0.001s — OK (100% passing)

# 3. Model Interaction Provenance Log
# File: reports/local_model_interactions.jsonl
# Audits all prompt templates, token response times, and local model inference metrics.
```

All changes are staged locally on branch `module/elm` and are ready for commit.
