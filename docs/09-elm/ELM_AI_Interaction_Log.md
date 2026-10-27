# ELM Assignment 6 — AI interaction log (chat-style retrospective)

**Source:** [ELM pilot branch](https://github.com/keptbeetle/Fusion-Integrated/tree/assignment6/elm-qwen25vl), [upstream PR #22](https://github.com/FusionIIIT/Fusion-Integrated/pull/22).
**Actual local model:** Qwen2.5-VL-7B (Q4_K_M quantized, 7B parameters) through LM Studio.
**Prompt interface:** Python script calling LM Studio's local OpenAI-compatible HTTP API, not Continue or Aider.
**Implementation commit:** 60f097fe59f7334b84717f0de9bb90d49476a5f6.

Note: LM Studio doesn't provide access to publically share chat link,this is only demonstration a actual prompts and outputs of the model


## Session 1 — Setup

**Developer → local Qwen (actual system prompt)**

~~~text

You are a Django 5.2 Python code generator working inside Fusion ERP. Return ONLY the complete requested Python file, without markdown or explanation. Avoid TODOs. Follow the exact named fields, unique constraints, and specifications.
~~~

**Prompt runner → LM Studio (recorded request settings)**

- API endpoint: http://127.0.0.1:1234/v1/chat/completions
- Model ID: qwen/qwen2.5-vl-7b
- Temperature: 0.05; max completion tokens: 2600
- Three file-specific user requests sent sequentially. The local model responded, and the script saved text into the ELM module tree.

## Session 2 — Generate modules/elm/models.py

**Developer → Qwen (exact original user prompt)**

~~~text
Create modules/elm/models.py for a pilot Employee Leave Management system. Models (all django.db.models, no user FK since IAM owns identities):
EmployeeLeaveProfile: user_id PositiveInteger unique, category choices faculty/staff, designation CharField blank, unit CharField, unit_head_user_id PositiveInteger null blank, sanction_authority_user_id PositiveInteger null blank; __str__.
LeaveBalance: employee_id PositiveInteger, year PositiveSmallInteger, category choices CL RH SCL EL COL VL; allotted and used DecimalField(max_digits=7,decimal_places=1,default=0), unique(employee_id, year, category) via UniqueConstraint; __str__.
Holiday: date DateField unique, name CharField, kind choices RH/CLOSED, published Boolean default false; __str__.
LeaveApplication: employee_id PositiveInteger; category same leave choices, start_date DateField end_date DateField, half_day CharField choices NONE/FIRST/SECOND default NONE, duration DecimalField(max_digits=7,decimal_places=1), reason TextField, station_leave Boolean default False, station_location CharField blank; status CharField choices PENDING/RECOMMENDED/APPROVED/REJECTED/WITHDRAWN default PENDING; unit_head_id PositiveInteger; sanction_authority_id PositiveInteger null blank; recommendation CharField blank; approver_id PositiveInteger null blank; decision_remarks TextField blank; decided_at DateTime null blank; created_at DateTime auto_now_add, updated_at auto_now; __str__.
LeaveEvent: application FK LeaveApplication related_name events on_delete PROTECT, actor_id PositiveInteger, action CharField, detail TextField blank, created_at DateTime auto_now_add; Meta ordering '-created_at'; __str__. Data max length sane, defaults for optional. Return valid concise code.
~~~

**LM Studio → Developer (actual completion metadata)**

- Model: qwen/qwen2.5-vl-7b
- Input tokens: 420; output tokens: 828; total: 1248; generated characters: 3594; finish reason: stop.

**Qwen → output (observed code excerpt)**

~~~python
class LeaveBalance(models.Model):
    # ...
    class Meta:
        unique_together = ['employee_id', 'year', 'category']
~~~

**Integrator → development notes (summary)**

The model wrapped the generated code in Markdown fences; it used unique_together instead of the specifically requested named UniqueConstraint and mislabeled RH as Religious Holiday and VL as Voluntary Leave. These were corrected when writing the Fusion-compatible ELM models. The final models use integer IAM IDs (no separate ELM login/user table).

**Outcome:** Corrected Django models were integrated, and the ELM initial migration was generated.

## Session 3 — Generate modules/elm/domain/policy.py

**Developer → Qwen (exact original user prompt)**

~~~text
Write pure standard-library modules/elm/domain/policy.py for ELM. Functions:
SUPPORTED=('CL','RH','SCL','EL','COL','VL') and DEFAULT_ENTITLEMENTS={'CL':8,'RH':2,'SCL':15,'EL':30,'COL':20,'VL':60}. Also CONTINUOUS={'EL','COL','VL'}.
 def eligible(category: str, employee_kind: str)->bool: return false unsupported; VL faculty only; EL can be faculty (converted VL) or staff; other types both.
 def count_days(category: str, start: date, end: date, half_day: str='NONE', closed_days: frozenset[date]=frozenset())->Decimal: reject end<start, unsupported, half_day only CL single day FIRST/SECOND. Halfday return Decimal('0.5'); continuous categories count EVERY calendar day in interval, other categories exclude weekends (weekday>=5) and closed_days, return Decimal value. raise ValueError if zero workdays.
 def overlaps(existing_start:date, existing_end:date, new_start:date, new_end:date, existing_half:str='NONE', new_half:str='NONE')->bool: date overlap true unless both are single same day, both halves are FIRST/SECOND and DIFFERENT. Any whole day overlap true.
 def remaining(allotted:Decimal,used:Decimal,requested:Decimal)->Decimal: reject negative/nonfinite, reject zero requested, reject overbalance; return allotted-used-requested. No Django imports. Return only code.
~~~

**LM Studio → Developer (actual completion metadata)**

- Model: qwen/qwen2.5-vl-7b
- Input tokens: 373; output tokens: 595; total: 968; generated characters: 2347; finish reason: stop.

**Qwen → output (observed code excerpts)**

~~~python
def eligible(category: str, employee_kind: str) -> bool:
    if category == 'VL':
        return False
~~~

~~~python
if category in CONTINUOUS and weekday >= 5 or closed_days.intersection(range(start, end)):
    days -= len(closed_days.intersection(range(start, end)))
~~~

**Integrator → development notes (summary)**

This rejected VL for everybody instead of just restricting eligibility to faculty. The counting logic referenced undefined weekday and used range on dates. Half-day overlap and remaining-balance calculations were also unsuitable. The pure-Python policy was corrected and focused tests added. The pilot service deliberately blocks VL requests pending academic-calendar integration: that is an explicit scope limitation, not the original Qwen error.

**Outcome:** Leave counting, overlaps, half-days, and decimal validation corrected.

## Session 4 — Generate modules/elm/registry.py

**Developer → Qwen (exact original user prompt)**

~~~text
Implement a Fusion ERP module registry modules/elm/registry.py. MODULE dict: code='leave_elm',label='Employee Leave Management',icon='CalendarBlank',base_path='/leave',nav_section='Leave',sort_order=25,status='active'. NAV_ITEMS list (code, label, icon, to, required_permission, sort_order): Apply at /leave/apply perm leave_elm.application.apply; My Applications /leave/mine perm leave_elm.application.view; Balances /leave/balance perm leave_elm.balance.view; Approvals /leave/approvals perm leave_elm.application.approve; Leave Admin /leave/admin perm leave_elm.policy.manage. PERMISSIONS list tuples exact: leave_elm.application.view, leave_elm.application.apply, leave_elm.application.approve, leave_elm.balance.view, leave_elm.policy.manage; description meaningful. ROLE_GRANTS mapping Employee to view/apply/balance; Leave Approver to approve/view/balance; Leave Admin to policy.manage/view/balance. SYSTEM_PERMISSIONS empty list. No extra permissions. Follow module placement/registry.py patterns. Return only code.
~~~

**LM Studio → Developer (actual completion metadata)**

- Model: qwen/qwen2.5-vl-7b
- Input tokens: 286; output tokens: 493; total: 779; generated characters: 2067; finish reason: stop.

**Qwen → output (observed code excerpt)**

~~~python
from django.apps import AppConfig

class LeaveEMLModule(AppConfig):
    name = 'leave_elm'
~~~

**Integrator → development notes (summary)**

Qwen produced an AppConfig class instead of the Fusion MODULE, NAV_ITEMS, PERMISSIONS, ROLE_GRANTS and SYSTEM_PERMISSIONS constants. Its role-grant entries did not use the fully qualified permission strings required by Fusion.

**Outcome:** Replaced with a compatible declarative registry and regenerated the permission manifest.

## Session 5 — Integrate the generated drafts with Fusion

**Integrator → Fusion repository (summarized work, NOT a Qwen prompt)**

- Registered modules.elm with Django and mounted its endpoints under /api/v1/elm/.
- Added a lazy-loaded /leave client route and five ELM pages (apply, history, balance, approvals, admin).
- Added IAM-backed permission checks, a database migration, transactional leave services, ownership checks and event history.
- Regenerated the generated permissions catalog and OpenAPI specification.
- Kept identity and permissions in Fusion IAM instead of duplicating login infrastructure.

**Attribution:** These significant additions and fixes were made with GPT-6 assistance. They are not correctly characterized as wholly generated by Qwen.

## Session 6 — Errors reported by Python lint

**Terminal → Integrator (observed Ruff messages)**

~~~text
modules\elm\api\serializers.py:1:1: I001 Import block is un-sorted or un-formatted
modules\elm\api\views.py:1:1: I001 Import block is un-sorted or un-formatted
modules\elm\api\views.py:19:48: F401 log_event imported but unused
modules\elm\domain\policy.py:50:5: SIM103 Return the negated condition directly
modules\elm\models.py:48:101: E501 Line too long
modules\elm\services\leave.py:3:1: I001 Import block is un-sorted or un-formatted
modules\elm\services\leave.py:43:101: E501 Line too long
modules\elm\services\leave.py:44:5: SIM102 Use a single if statement instead of nested if statements
Found 8 errors.
~~~

**Integrator → Terminal (summary)**

Applied Ruff formatting, automatically fixed safe import issues, simplified conditional logic and reran checks.

**Terminal → Integrator (actual final result)**

~~~text
All checks passed!
~~~

## Session 7 — Migration generation interruption

**Integrator → Terminal:** Attempted Django makemigrations elm --noinput.

**Terminal / process observation:** The migration command failed to complete normally and was stopped; it must not be reported as a successful run.

**Integrator → Terminal (summary):** Used Django MigrationAutodetector and MigrationWriter to produce the initial migration without a database-dependent interactive command, then compared models with migration state.

**Terminal → Integrator (actual resulting check)**

~~~text
Created ...\modules\elm\migrations\0001_initial.py
All detected changes: {}
~~~

## Session 8 — OpenAPI schema conflicts

**Terminal → Integrator (observed warnings)**

~~~text
Warning [BalancesAdminView > BalanceSerializer]: unable to resolve type hint for function "get_available".
Warning [ApplicationListView > ApplicationSerializer]: Encountered 2 components with identical names "Application" and different identities.
Warning: enum naming encountered a non-optimally resolvable collision for fields named "category".
SchemaGenerationError: Failing as requested due to warnings
~~~

**Integrator → Terminal (summary)**

Renamed the ELM application serializer, supplied schema field metadata and resolved conflicting profile/category representations.

**Terminal → Integrator (observed result)**

The strict OpenAPI generation command completed successfully after these corrections.

## Session 9 — Verification

**Integrator → Terminal (summary):** Ran focused checks that confirm Fusion integration without claiming a production-ready ELM implementation.

| Check | Recorded outcome |
| --- | --- |
| Django system check | System check identified no issues (0 silenced). |
| ELM policy tests | Six tests passed |
| Repository-wide Ruff lint | All checks passed! |
| Permission manifest | permission manifest matches the registries |
| Navigation routes | nav items and client routes agree |
| Cross-module foreign keys | no cross-module foreign keys |
| Contracts getter shape | all contract getters are plural |
| Import linter | 4 contracts kept, 0 broken |
| TypeScript type check | exited successfully |
| Vite frontend build | built in 6.01s; emitted a 500 kB chunk-size warning |
| Offline model/migration comparison | All detected changes: {} |
| OpenAPI schema generation | succeeded after warnings were corrected |

No live clean IAM/PostgreSQL end-to-end deployment was verified.

## Session 10 — Git submission

**Integrator → Git (recorded result)**

~~~text
60f097fe59f7334b84717f0de9bb90d49476a5f6
feat(elm): add Assignment 6 leave management pilot
27 files changed, 1863 insertions(+)
~~~

The branch assignment6/elm-qwen25vl was pushed to the keptbeetle fork and opened as [FusionIIIT/Fusion-Integrated PR #22](https://github.com/FusionIIIT/Fusion-Integrated/pull/22).

## Interpretation and limitations

The LM Studio model genuinely produced three initial file drafts, but they were not fully usable without correction and significant integration work. The final pilot has a limited leave workflow, not all 32 coherent ELM functional requirements. For details, see [assignment6-pilot.md](assignment6-pilot.md).


