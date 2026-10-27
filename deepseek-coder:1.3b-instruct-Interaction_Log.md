# DeepSeek-Coder 1.3B Instruct — ELM Interaction Log

**Assignment:** Fusion ERP Lab — Assignment 6 (Phase 1 baseline and Phase 2 review/improvement)  
**Model:** `deepseek-coder:1.3b-instruct`, run locally using Ollama  
**Repository:** [SaloniKapadnis9004/Fusion-Integrated](https://github.com/SaloniKapadnis9004/Fusion-Integrated)  
**Phase 2 pull request:** [PR #362 — Phase 2: Improve ELM workflow validation and cancellation](https://github.com/FusionIIIT/Fusion-Integrated/pull/362)

> **How this log was compiled:** This log was assembled from the two command/settings conversation exports and the Phase 2 pull-request summary. The terminal commands and results below are based on the captured records. The natural-language task descriptions are reconstructed summaries of the work, not verbatim copies of the original prompts sent to the local model. The available exports do not preserve a complete model chat transcript.

## 1. Objective

Use the locally deployed DeepSeek-Coder model as the Phase 1 code-generation baseline, then review and improve the generated ELM code for integration with the existing Fusion-Integrated Django project. The work included repository setup, configuration and dependency troubleshooting, URL/app integration, migration investigation, testing, and focused Phase 2 changes to leave-request validation, cancellation workflows, API integration, and permissions.

## 2. Interaction timeline

### Interaction 1 — Prepare the repository and create a DeepSeek branch

**Reconstructed task summary**

> Work in the existing Fusion-Integrated repository. Synchronize the local main branch with the upstream repository, create a separate branch for the DeepSeek-generated ELM implementation, and keep the work isolated from main.

**Commands recorded**
```bat
cd C:\Users\ADMIN\Fusion-Integrated
git status
git checkout -b sub-branch-24bcs114-granite4
git stash
git checkout main
git pull origin main
git checkout -b sub-branch-24bcs114--deepseek
```

**Observed outcome**
- The starting `main` working tree was clean.
- Upstream `main` was updated before creating the DeepSeek branch.
- A branch named `sub-branch-24bcs114--deepseek` was created.
- The first attempt to create the branch contained pasted formatting text and failed; the command was then run correctly.

### Interaction 2 — Generate and commit an initial ELM scaffold

**Reconstructed task summary**

> Create the initial files for an ELM Django module, including models, forms, views, URLs, and templates, so the generated implementation can be committed and reviewed.

**Commands recorded**
```bat
mkdir elm\templates\elm
type nul > elm\__init__.py
type nul > elm\models.py
type nul > elm\views.py
type nul > elm\urls.py
type nul > elm\forms.py
type nul > elm\templates\elm\courses.html
type nul > elm\templates\elm\course_detail.html
git add .
git commit -m "feat: integrate ELM module using deepseek-coder:1.3b-instruct"
```

**Observed outcome**
The captured commit was `ba4bfa8` and reported seven files changed. The generated files included generic `ELearningCourse`, `Evaluation`, `Leave`, and `Module` models and course-oriented templates/views. During later review, this scaffold was a clear signal that generated code needed to be checked against the actual employee leave-management requirements rather than accepted based on file creation alone.

### Interaction 3 — Correct the Git remote and push the branch

**Task summary**
> Push the new implementation branch to our own fork and resolve the upstream repository permission error.

**Commands recorded**
```bat
git push origin sub-branch-24bcs114--deepseek
git remote set-url origin https://github.com/SaloniKapadnis9004/Fusion-Integrated.git
git push origin sub-branch-24bcs114--deepseek
```

**Observed outcome**
The first push failed with HTTP 403 because `origin` pointed at `FusionIIIT/Fusion-Integrated`, where the account did not have direct push permission. After changing `origin` to the personal fork, the branch push succeeded.

### Interaction 4 — Set up Python dependencies for local execution

**Reconstructed task summary**

> Diagnose why the Django management commands do not run, install the project's dependencies using its declared project configuration, and verify that Django can load the application settings.

**Issues and commands recorded**
- `python manage.py shell ...` first failed with `ModuleNotFoundError: No module named 'django'`.
- `poetry` was not initially available on PATH, and `requirements.txt` did not exist at the repository root.
- Creating a virtual environment and installing an old Poetry release led to a `six.moves` import error.
- Missing packages such as `django_cors_headers`, `django_filters`, and `drf_spectacular` were encountered as setup progressed.
- The project dependencies were then installed from the project metadata using:

```bat
python -m venv venv
venv\Scripts\activate
pip install -e .
```

**Observed outcome**
The editable project install installed the dependencies declared by the repository, including Django 5.2.18 and the project's API/documentation dependencies. This was more aligned with the repo than relying on a nonexistent `requirements.txt` file.

### Interaction 5 — Check app registration and generated migrations

**Commands recorded**
```bat
python manage.py shell -c "from django.conf import settings; print('elm' in settings.INSTALLED_APPS)"
python manage.py makemigrations elm
```

**Observed outcome**
- The first settings check printed `False`; after a settings edit, a subsequent check printed `True`.
- `makemigrations elm` created `elm\\migrations\\0001_initial.py` for `ELearningCourse`, `Evaluation`, `Leave`, and `Module`.

**Review finding**
Those model names reflected a generic generated scaffold rather than a complete, validated ELM domain model. The generated migration was therefore not by itself evidence that the leave-management requirements had been implemented correctly. This was one of the reasons for reviewing and improving the implementation instead of treating generated code as final.

### Interaction 6 — Diagnose database configuration and migration failures

**Reconstructed task summary**

> The application cannot connect to the configured database in the local environment. Identify a safe local testing approach, run migrations, and distinguish environment-specific migration failures from application behaviour.

**Observed issues and changes**
- The initial PostgreSQL connection timed out during `makemigrations`/ `migrate`.
- The captured local diff temporarily changed `config/settings/base.py` from PostgreSQL environment-variable configuration to SQLite (`db.sqlite3`).
- `config/settings/dev.py` was changed to register the ELM app.
- Migrations then encountered placement-schema errors, including `no such index: document_profile_idx` and a later `no such table: placement_offer`.
- The local session used `--fake` for affected placement migration states, then reran migrations.

**Commands recorded**
```bat
python manage.py makemigrations elm
python manage.py migrate
python manage.py migrate placement 0010 --fake
python manage.py migrate
```

**Outcome and caveat**
The terminal record shows that some migrations applied and some placement migrations were faked to get past a local schema/history mismatch. This was a diagnostic workaround for the local database, not proof that the historical placement migrations or a production database were correct. A global SQLite change in `base.py` should not be treated as a production configuration; local test settings should isolate the SQLite override.

### Interaction 7 — Wire ELM URLs and inspect import errors

**Reconstructed task summary**

> Register the ELM endpoints in the Django URL configuration and verify that the application can import the route module.

**Observed issues**
- The URL configuration was edited to include `modules.elm.api.urls`; the runserver autoreloader reported `ModuleNotFoundError: No module named 'modules.elm'` in that state.
- The route was then changed to `elm.api.urls`; the next startup reported `ModuleNotFoundError: No module named 'elm.api'`.
- The initial generic scaffold did not contain a corresponding API package in the form expected by these routes.

**Outcome**
The failures exposed a mismatch between the route configuration and the files actually present in the generated scaffold. They reinforced the need to check package paths and endpoint implementations together, rather than only adding an `include(...)` statement.

### Interaction 8 — Run the initial test commands and inspect Git changes

**Commands recorded**
```bat
python manage.py test
python manage.py test elm
git status
git branch --show-current
git log -1 --oneline
git diff > phase2_initial_changes.patch
git diff --stat
git diff -- config/settings/base.py config/settings/dev.py config/urls.py
```

**Observed results**
- `python manage.py test`: 61 tests were found and passed; Django reported no system-check issues.
- `python manage.py test elm`: found 0 tests and printed `NO TESTS RAN`. This was not a successful ELM-specific test run; it showed that the early scaffold did not provide discoverable tests under that label.
- The local diff showed edits to database settings, app registration, and URL configuration, along with untracked migration/scaffold artifacts.
- A patch file, `phase2_initial_changes.patch`, was created to capture the working diff.

**Interpretation**
The general project test suite passing was useful, but the zero-test ELM command did not validate ELM workflow behaviour. The generated code and integration errors required focused ELM tests and further implementation work.

### Interaction 9 — Improve the Phase 2 ELM implementation

**Reconstructed task summary**

> Review the generated ELM implementation against the repository architecture and leave-management workflow. Strengthen request validation, add cancellation request/decision handling, integrate the API endpoints with permission checks, and update the ELM permission registry and generated permission manifest. Make focused changes and verify them with the available ELM checks.

**Changes described by Phase 2 PR #362**
- Improved leave-request validation, including rejection of invalid requested-day values.
- Added leave-cancellation request and decision workflows.
- Integrated ELM API endpoints and permission checks.
- Updated the ELM permission registry and generated permission manifest.

**Pull request**
[PR #362 — Phase 2: Improve ELM workflow validation and cancellation](https://github.com/FusionIIIT/Fusion-Integrated/pull/362)

**Validation reported in the pull-request description**
- Django system checks passed.
- 22 ELM tests passed using diagnostic settings.
- Permission-manifest validation passed.
- No unexpected model migration changes were detected.

These Phase 2 results are distinct from the earlier terminal run that found 61 general tests and 0 tests under `elm`; the two test outcomes should not be merged into one claim.

## 3. Key repository and configuration areas

| Area | Work / observation |
|---|---|
| Initial generated scaffold | `elm/models.py`, `elm/forms.py`, `elm/views.py`, `elm/urls.py`, and templates under `elm/templates/elm/` |
| App configuration | `config/settings/dev.py`; a local check was used to see whether `elm` was registered |
| Database configuration | `config/settings/base.py` was temporarily changed from PostgreSQL to SQLite in the local session; treat this as a diagnostic workaround, not the production setup |
| URL routing | `config/urls.py` was edited to add ELM routes; initial route attempts failed because the referenced API package was missing |
| Diff review | `git diff --stat`, targeted `git diff`, and `phase2_initial_changes.patch` |
| Phase 2 PR | [FusionIIIT/Fusion-Integrated#362](https://github.com/FusionIIIT/Fusion-Integrated/pull/362) |

## 4. Lessons from using a small local code model

The main lesson was that producing files is not the same as implementing a correct module. The initial scaffold included course/evaluation-oriented models and templates, lacked the API package referenced by the route configuration, and had no ELM tests discoverable with `python manage.py test elm`. Repository-level work therefore needed human review of the domain model, settings, imports, migrations, permissions, and test coverage. The Phase 2 work focused on improving the relevant leave-request and cancellation workflows and verifying those improvements with ELM-specific checks.

## 5. Evidence and limitations

- The terminal commands and outputs in this log are grounded in the supplied command/settings captures.
- The pull-request validation results are taken from the summary of PR #362.
- Task descriptions are reconstructed summaries, not exact historical user prompts or a transcript of every response from Ollama/DeepSeek.
- The early SQLite and `--fake` migration actions were local diagnostic workarounds; they should not be represented as production migration steps.
- The 61-test repository run and the later 22-test ELM diagnostic run are different test runs.
- The log records the process and evidence available; it does not claim that every possible leave lifecycle or production integration scenario was tested.
