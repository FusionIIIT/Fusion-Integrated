You are an expert Django 4 and DRF developer working on the Fusion-Integrated repository. Your task is to finalize the modules/leave/ application by executing the following 6 steps in order. I will provide the output of all verification commands between steps.

P1 (Registration): Add "modules.leave" to DOMAIN_MODULES in config/settings/base.py. Create modules/leave/api/urls.py to map all views with a leave- prefix, and include it in config/urls.py.Verification: Wait for me to run manage.py check and provide the output.

P2 (Migrations): Create an empty modules/leave/migrations/__init__.py file and ensure modules/leave/apps.py has label="leave".Verification: Wait for me to run manage.py makemigrations leave and manage.py migrate and provide the outputs.

P3 (Domain Rules): Fix modules/leave/domain/categories.py to meet these exact business rules:

BR-EL-007: EL = VL / 2 (use fractional decimal division).

BR-EL-011: CL/SCL count must exclude both Saturday and Sunday.

BR-EL-012: Same-date half-day leaves overlap only if they occupy the same half.
Create test_domain_rules.py containing these test cases.Verification: Wait for me to run pytest modules/leave/tests/test_domain_rules.py -v and provide the output.

P4 (API Tests): Write test_api.py covering the full workflow (apply, extend, resume) and authorization (return 404 for out-of-scope requests, 403 for missing permissions).Verification: Wait for me to run pytest modules/leave/tests/ -v and provide the output.

P5 (Registry): Validate NAV_ITEMS and ROLE_GRANTS in modules/leave/registry.py. Change MODULE["status"] from "planned" to "active".Verification: Wait for me to run manage.py permission_manifest --check and provide the output.

P6 (CI & Wrap-up): Output the final Phase-2 report detailing spec violations fixed, tests added, and integration gaps closed.Verification: Wait for me to run make check (and make schema if needed) and provide the final CI output.

Fallback Rule: If any step fails during verification, diagnose the error in 3 lines maximum and provide the exact minimal patch for the specific file before proceeding.