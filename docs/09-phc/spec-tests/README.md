# PHC test evidence

The executable strategy suites live at `modules/phc/tests/`. The `design/` folder contains the four specification-derived design JSON files. The `results/` folder contains the first-run triage evidence, final strategy logs, JUnit XML, coverage XML, and static-check logs.

## Run the PHC tests

From the repository root in PowerShell, install the project development dependencies:

```powershell
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
```

The checked-in test settings use PostgreSQL, as the repository does in CI. Start Docker Desktop, then run:

```powershell
$env:DB_PASSWORD = "phc-local-test"
docker compose up -d db
$p = ".\.venv\Scripts\python.exe"
foreach ($s in @("fr", "uc", "br", "wf")) {
  $out = "docs\09-phc\spec-tests\results\$s"
  & $p -m pytest "modules\phc\tests\test_$s.py" -q `
    --ds=config.settings.test `
    --junitxml="$out\junit.xml" `
    --cov=modules.phc `
    --cov-report="xml:$out\coverage.xml" `
    --cov-report=term *> "$out\pytest.log"
  if ($LASTEXITCODE -ne 0) { throw "PHC $s suite failed" }
}
```

The committed result files were generated earlier using a temporary SQLite-only settings override because Docker Desktop was unavailable. That local override is intentionally not part of the PR. Its results are not PostgreSQL results; rerun with the repository's normal Postgres test settings before claiming PostgreSQL validation. Exact commands used for the recorded results are in `quality-report.md`.
