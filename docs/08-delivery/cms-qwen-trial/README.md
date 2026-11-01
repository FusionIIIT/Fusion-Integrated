# CMS local-model trial evidence

One genuine local Ollama Qwen2.5-Coder 3B one-shot trial for the Complaint Management System (`complaint_cms`). The changes are prepared on `codex/cms-qwen-trial`.

- [TRIAL_RECORD.md](TRIAL_RECORD.md): model-generated report, checked against recorded results.
- [prompts.md](prompts.md): every exact system/user prompt and options, in order.
- [responses/](responses/): exact API requests, original outputs, timing/token statistics and before-files.
- [mechanical-corrections.md](mechanical-corrections.md): supervised mechanical integration corrections.
- [checks.log](checks.log) and [checks.jsonl](checks.jsonl): actual commands, stdout/stderr, exit codes and timing.
- [observed-results.json](observed-results.json): aggregate evidence at the end of code generation.
- [trial-metadata.json](trial-metadata.json): installed model digest, quantization, runtime, hardware and official Fusion base commit.
- [file-inventory.json](file-inventory.json): final application-file hashes.
- [jobs/](jobs/): request plans (`responses/*.request.json` and `prompts.md` establish what was actually sent).
- [check-settings/](check-settings/): temporary build configuration templates; no production secrets or database content.

## Scope

Checks cover compilation and mechanical integration only. No functional tests, business-rule validation, requirements-gap audit, security hardening, maintainability changes or optimization were performed. The model's logic and field assumptions are retained. No deliberate bugs were inserted.

The frontend production build (`npm run build`), TypeScript check (`tsc --noEmit`), backend system check (`manage.py check`), Python compilation, import boundaries (`lint-imports`), cross-module FK check (`no_cross_module_fk.py`), navigation registration (`nav_matches_routes.py`), schema drift check (`makemigrations --check --dry-run`), module seeding (`seed_modules`), and isolated CMS migration (`manage.py migrate`) all passed.

## Commands

With Ollama running and `qwen2.5-coder:3b` already installed:

```sh
python3 devtools/qwen_cms_trial.py generate docs/08-delivery/cms-qwen-trial/jobs/05-queries.json
```

The check runner uses the temporary configuration in `check-environment.json` and recreates it from the saved templates if absent:

```sh
.venv/bin/python devtools/cms_trial_check.py --label django-check -- .venv/bin/python manage.py check
.venv/bin/python devtools/cms_trial_check.py --label cms-schema --isolated -- .venv/bin/python manage.py migrate --noinput
.venv/bin/python devtools/cms_trial_check.py --label frontend-build --client -- npm run build
```
