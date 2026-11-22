# PHC specification test evidence

The four executable pytest strategies are in `modules/phc/tests/`: FR, UC, BR, and WF. The expanded final run contains **215 passing cases**: FR 60, UC 76, BR 54, and WF 25. Combined coverage is 97.71% line and 93.14% branch. These values are from the saved machine-generated reports under `results/expanded-final/`; earlier failed runs and triage are retained separately.

The design files are in `docs/09-phc/design/`. They were prepared after implementation was visible, as recorded in each design file and the quality report.

## Reproduce in a PostgreSQL environment

The repository's normal test settings use PostgreSQL. With Docker Desktop's Linux engine running, from the repository root run:

```powershell
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
$env:DB_PASSWORD = "phc-local-test"
docker compose up -d db
$p = ".\.venv\Scripts\python.exe"
$cov = @('--cov=modules.phc.api','--cov=modules.phc.domain','--cov=modules.phc.models','--cov=modules.phc.selectors','--cov=modules.phc.services','--cov-branch','--cov-report=term')
foreach ($s in @("fr", "uc", "br", "wf")) {
  $out = "docs\09-phc\spec-tests\results\expanded-final\$s"
  & $p -m pytest "modules\phc\tests\test_$s.py" --ds=config.settings.test `
    "--junitxml=$out\junit.xml" @cov "--cov-report=xml:$out\coverage.xml" *> "$out\pytest.log"
  if ($LASTEXITCODE -ne 0) { throw "PHC $s suite failed" }
}
```

The combined command uses `modules\phc\tests` in place of a strategy file and writes to `results\expanded-final\all\`.

## Recorded run environment

The saved final reports in this branch were generated with a temporary SQLite test-settings override because Docker Desktop could not start its Linux engine on the recording machine. The override kept the PHC migration active and disabled unrelated Directory, Placement, and Access Control migrations. It was removed after the run and is not checked in. The exact commands, initial findings, and environment details are in [`../quality-report.md`](../quality-report.md) and [`triage.md`](triage.md). A PostgreSQL run should replace these SQLite results before claiming PostgreSQL validation.
