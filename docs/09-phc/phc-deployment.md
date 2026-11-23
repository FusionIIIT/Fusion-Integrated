# PHC deployment order

Run these in order on each environment. Each step is safe to repeat.

1. **Migrate** (Fusion-Integrated):
   ```bash
   .venv/bin/python manage.py migrate
   ```
2. **Configure the reimbursement window** (PHC-BR-06). The value comes from the institute; a new
   version supersedes the old one from its effective date, and no version is ever edited:
   ```bash
   .venv/bin/python manage.py phc_configure_window --days <n> --includes-last-day yes|no
   ```
3. **Register the module and its navigation** (Fusion-Integrated). Without step 2 this registers
   PHC as `planned` and prints the unmet prerequisite:
   ```bash
   .venv/bin/python manage.py seed_modules
   ```
4. **Publish permissions to the IAM** (Fusion-Integrated, then Fusion_System_Administrator). Read the
   output: seeding is authoritative for PHC, and it names every grant it revokes:
   ```bash
   make permissions
   cd <Fusion_System_Administrator>/Backend/backend && ./../venv/bin/python manage.py \
     seed_iam_permissions --manifest <Fusion-Integrated>/registry/permissions.json
   ```
5. **Grant the office designations** (Fusion_System_Administrator). In production the academic office
   creates and assigns these; for testing, from `Backend/backend`:
   ```bash
   ./../venv/bin/python manage.py assign_role --user <username> --designation "PHC Staff"
   ./../venv/bin/python manage.py assign_role --user <username> --designation "Accounts & Audit"
   ./../venv/bin/python manage.py assign_role --user <username> --designation "Approving Authority"
   ```
   The person who decides requisitions must not be the PHC Staff member who raises them.
6. **Check readiness** (Fusion-Integrated). It exits non-zero and names each unmet prerequisite:
   ```bash
   .venv/bin/python manage.py phc_readiness
   ```

PHC has no scheduled tasks, so no Celery beat entry needs to be running for it.

The `Fusion-client` sidebar entry, for whoever maintains `INTEGRATED_MODULES`:
`{ id: "phc", label: "Primary Health Centre", icon: "FirstAidKit", to: "/phc", section: "Health Services" }`.
