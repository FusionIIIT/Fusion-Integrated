# Phase 1 AI Interaction Log — DeepSeek-Coder 1.3B Instruct

**Assignment:** Fusion ERP Lab — Assignment 6, Phase 1: Local AI Coding Model Experiment  
**Model:** `deepseek-coder:1.3b-instruct`  
**Runtime:** Ollama (local model execution)  
**Repository:** [SaloniKapadnis9004/Fusion-Integrated](https://github.com/SaloniKapadnis9004/Fusion-Integrated)  
**Phase 1 pull request:** [PR #177 — integrate ELM module using deepseek-coder:1.3b-instruct](https://github.com/FusionIIIT/Fusion-Integrated/pull/177)

> **Log scope and accuracy:** This log is limited to the Phase 1 initial generation and submission of the DeepSeek implementation. The repository commands and initial PR contents are based on the available command transcript and PR diff. Since a complete raw Ollama/chat prompt transcript was not preserved in the available records, the natural-language task descriptions below are reconstructed summaries, not verbatim prompts.

## 1. Objective

Use a locally deployed coding model, DeepSeek-Coder 1.3B Instruct, to generate an initial Employee Leave Management (ELM) Django implementation within the Fusion-Integrated repository. Commit the generated files on a separate Git branch and submit the result for review.

## 2. Model setup and task

The selected model tag recorded for this implementation was:

```text
deepseek-coder:1.3b-instruct
```

The model was used locally through Ollama for the Phase 1 code-generation experiment. The available transcript confirms the selected model through the Git commit message and pull-request title, but it does not include the original full Ollama prompt/response transcript.

**Reconstructed task summary**

> Generate a basic Django implementation for an Employee Leave Management module inside the existing Fusion-Integrated repository. Create the initial model, form, view, URL, and template files, and keep the implementation organized as a separate module that can be committed and reviewed.

## 3. Initial repository preparation

The terminal transcript records starting from a clean working tree, updating the upstream `main` branch, and creating a separate branch for the DeepSeek implementation.

**Commands recorded**

```bat
cd C:\Users\ADMIN\Fusion-Integrated
git status
git checkout main
git pull origin main
git checkout -b sub-branch-24bcs114--deepseek
```

A separate experimental branch named `sub-branch-24bcs114-granite4` was also created during setup. The DeepSeek implementation itself was committed on `sub-branch-24bcs114--deepseek`.

## 4. Initial code generation

The terminal record shows creation of a Django file structure for the generated implementation:

```bat
mkdir elm\templates\elm
type nul > elm\__init__.py
type nul > elm\models.py
type nul > elm\views.py
type nul > elm\urls.py
type nul > elm\forms.py
type nul > elm\templates\elm\courses.html
type nul > elm\templates\elm\course_detail.html
```

The resulting initial implementation, as visible in the Phase 1 pull-request diff, contained the following elements.

| File / area | Initial generated scaffold |
|---|---|
| `elm/models.py` | Django models named `ELearningCourse`, `Evaluation`, `Leave`, and `Module`, with title/description and timestamps. |
| `elm/forms.py` | Model forms for the course, evaluation, leave, and module models. |
| `elm/views.py` | Course-list and course-detail views. |
| `elm/urls.py` | URL patterns for course list and course detail pages. |
| `elm/templates/elm/courses.html` | Basic list template showing available courses. |
| `elm/templates/elm/course_detail.html` | Basic course detail template. |

**Initial result:** The generated files established an initial Django scaffold and demonstrated local code generation and repository integration. The contents were not yet a complete, verified leave-management workflow: several models and pages were generic course/evaluation scaffolding, and the captured initial files did not show full leave application, approval, balance, cancellation, or permission logic. These gaps were part of the reason further review and improvement were needed in Phase 2.

## 5. Commit and push

The terminal transcript records committing the initial files with a commit message naming the selected DeepSeek model.

**Commands recorded**

```bat
git add .
git commit -m "feat: integrate ELM module using deepseek-coder:1.3b-instruct"
git push origin sub-branch-24bcs114--deepseek
```

The commit output recorded commit `ba4bfa8` and seven files changed.

The first push attempt failed with HTTP 403 because `origin` pointed to the upstream `FusionIIIT/Fusion-Integrated` repository, where the account did not have push permission. The remote was then changed to the personal fork and the branch push succeeded:

```bat
git remote set-url origin https://github.com/SaloniKapadnis9004/Fusion-Integrated.git
git push origin sub-branch-24bcs114--deepseek
```

## 6. Phase 1 pull request

The initial DeepSeek implementation was submitted through:

**[PR #177 — integrate ELM module using deepseek-coder:1.3b-instruct](https://github.com/FusionIIIT/Fusion-Integrated/pull/177)**

This PR corresponds to the initial scaffold produced for the DeepSeek Phase 1 experiment. Its code should be interpreted as the Phase 1 baseline, not as the improved Phase 2 implementation.

## 7. Phase 1 outcome and limitation

The experiment produced a committed and pushed Django scaffold generated with the selected local coding model. The most important limitation visible in the delivered code was that the generated output was generic and incomplete for a real ELM workflow. Human review was needed to compare the files against the actual domain requirements and the Fusion project's conventions.

Phase 2 therefore followed as a separate stage to review the baseline, address implementation gaps, and improve validation, cancellation handling, API integration, and permissions. Those follow-up activities are documented separately in the [Phase 2 AI Interaction Log](https://github.com/SaloniKapadnis9004/Fusion-Integrated/blob/elm-phase2-correct/docs/elm/Phase-2-AI-Interaction-Log.md) and [Phase 2 PR #362](https://github.com/FusionIIIT/Fusion-Integrated/pull/362).

## 8. Evidence note

This document is a Phase 1 activity log compiled from the available command capture and the repository's Phase 1 pull-request diff. It includes actual recorded Git commands and describes the code visible in PR #177. The natural-language prompt above is a reconstruction of the task, not a verbatim historical prompt. No claim is made that the file reproduces every original prompt or response from the local model.
