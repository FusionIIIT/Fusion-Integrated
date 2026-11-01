# Mechanical integration corrections

Registered `modules.complaint_cms` in `config/settings/base.py` (`DOMAIN_MODULES`), mounted `api/v1/complaints/` in `config/urls.py`, merged `BEAT_SCHEDULE` and `TASK_ROUTES` in `config/celery.py`, added `complaint_cms` to `.importlinter` domain/module/layer contracts, and registered `complaint_cms` in `client/src/app/registry.ts`. Exact diff: `integration-registration.patch`.

Created empty Python package `__init__.py` files for `modules/complaint_cms/`, `domain/`, `services/`, `api/`, and `migrations/` as mechanical package scaffolding. Application logic remains model-generated.

Prompt 001 (`modules/complaint_cms/models.py`): added missing `from dataclasses import dataclass` import for the placeholder `Principal` dataclass and increased `status` / `update_type` / `old_status` / `new_status` `max_length` from `10` to `20` to satisfy Django `fields.E009` (`'In Progress'` is 11 chars and `'StatusChange'` is 12 chars). Model fields, choices, and defaults were preserved unchanged.

Prompt 002 (`modules/complaint_cms/registry.py`): aligned `NAV_ITEMS` dictionary keys (`code`, `label`, `icon`, `to`, `required_permission`, `sort_order`) with the required `seed_modules` / `nav_matches_routes.py` contract and granted `complaint_cms.task.view` to authority roles so every declared permission has a holder.

Prompt 004 (`modules/complaint_cms/contracts.py`): added missing `from dataclasses import dataclass` import and aliased `UserScopedModel as UserRef` to match the generated query without changing contract logic.

Prompts 005–008 (`modules/complaint_cms/services/*.py`): adapted single-dot relative imports (`.models`, `.domain.policy`, `.registry`) to parent package relative imports (`..models`, `..domain.policy`, `..registry`), mapped exception imports to `core.api.exceptions`, and replaced `pytz` with `django.utils.timezone` in `events.py`. All query filters, submission logic, workflow action branches, and scheduled event bodies were preserved unchanged.

Prompt 009 (`modules/complaint_cms/tasks.py`, `schedule.py`): added missing `@shared_task` decorator to `cms_process_sla` and removed unused `pytz` import in `schedule.py`.

Prompts 010–013 (`modules/complaint_cms/api/*.py`): adapted single-dot model/service imports to `..models` / `..services`, imported `HasModuleGrant` and `HasPermission` from `fusion_auth.permissions`, replaced invalid `CharField(choices=...)` with `ChoiceField(choices=...)` and `null=True`/`blank=True` with `allow_null=True`/`allow_blank=True` on DRF serializer field overrides, wrapped `record_list_view` in `RecordListView(APIView)` to match the generated `urls.py` import, and stripped trailing slashes in `urls.py` to match the platform API convention.

Prompts 014–019 (`client/src/modules/complaint_cms/**`): added `export` keywords to `api.ts` functions and re-exported `./types`, added `Navigate` import in `routes.tsx`, and adapted React Query v5 object-form calls (`useQuery({ queryKey, queryFn })`, `useMutation({ mutationFn })`, `invalidateQueries({ queryKey })`), Mantine v7 component props (`gap`, `justify`, `highlightOnHover`, `value` on `Pagination`), and named imports (`{ PageHeader }`, `{ errorMessage }`) so `tsc --noEmit` and `npm run build` succeed without altering generated UI structure or API payloads.
