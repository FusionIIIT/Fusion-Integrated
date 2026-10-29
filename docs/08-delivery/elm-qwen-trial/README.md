# ELM local-model trial evidence

One genuine local Ollama Qwen2.5-Coder 3B trial. The changes are prepared on `codex/elm-qwen-trial`.

- [TRIAL_RECORD.md](TRIAL_RECORD.md): model-generated report, checked against recorded results.
- [prompts.md](prompts.md): every exact system/user prompt and options, in order.
- [responses/](responses/): exact API requests, original outputs, timing/token statistics and before-files. Failed responses are retained.
- [mechanical-corrections.md](mechanical-corrections.md): supervised mechanical integration corrections.
- [checks.log](checks.log) and [checks.jsonl](checks.jsonl): actual commands, stdout/stderr, exit codes and timing.
- [observed-results.json](observed-results.json): aggregate evidence at the end of code generation (documentation calls are recorded separately in responses).
- [trial-metadata.json](trial-metadata.json): installed model digest, quantization, runtime, hardware and official Fusion base commit.
- [specification-source.json](specification-source.json): supplied ZIP hash and extraction source.
- [file-inventory.json](file-inventory.json): final application-file hashes.
- [jobs/](jobs/): request plans. Some plans were never executed; responses/*.request.json and prompts.md establish what was actually sent.
- [check-settings/](check-settings/): temporary build configuration templates; no production secrets or database content.

## Scope

Checks cover compilation and mechanical integration only. No functional tests, business-rule validation, requirements-gap audit, security hardening, maintainability changes or optimization were performed. The model's logic and field assumptions are retained. No deliberate bugs were inserted. The generation failures and recorded interventions describe this run, not a controlled benchmark of model efficiency.

The frontend production build, backend system check/compilation, import boundaries, navigation registration, schema drift check and isolated ELM migration passed. The full temporary SQLite Fusion migration failed in existing Placement0009 (`document_profile_idx` missing); ELM0001 installed before that failure. Actual PostgreSQL and workflow behavior are unverified.

## Commands

With Ollama running and `qwen2.5-coder:3b` already installed:

```sh
python3 devtools/qwen_elm_trial.py generate docs/08-delivery/elm-qwen-trial/jobs/02h-queries-small.json
```

This appends a new prompt/response log and overwrites the requested generated file. Per-call parameters changed during the recorded trial; use the saved request JSON for an exact request configuration. Model output is not guaranteed identical.

The check runner uses the temporary configuration in `check-environment.json`, and recreates it from the saved templates if absent. It does not use the project's real database:

```sh
.venv/bin/python devtools/elm_trial_check.py --label django-check -- .venv/bin/python manage.py check
.venv/bin/python devtools/elm_trial_check.py --label elm-schema --isolated -- .venv/bin/python manage.py migrate --noinput
.venv/bin/python devtools/elm_trial_check.py --label frontend-build --client -- npm run build
```

Review `mechanical-corrections.md` alongside the raw responses before attributing the final build entirely to the model. PR publication and form submission are pending.
