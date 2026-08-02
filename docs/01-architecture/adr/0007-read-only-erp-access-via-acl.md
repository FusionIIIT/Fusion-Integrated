# ADR-0007 — Read the ERP only through `modules/academics`, on a read-only role

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0008](0008-declared-academic-snapshot-for-cpi.md), [0012](0012-postgres-roles-and-least-privilege.md), [0013](0013-no-cross-module-foreign-keys.md)

## Context

The platform needs academic facts: which students exist, their batch and discipline, and their declared
CPI. All of that lives in the ERP database, which the legacy monolith owns and actively develops.

The ERP's vocabulary is not merely different — it is actively misleading, and several of its traps have
already caused bugs in the code we are replacing:

| ERP reality | Why it is a trap |
|---|---|
| `Student.cpi` is permanently `0.0` — only writers set it to zero at creation | The deprecated placement module filters `cpi__gte=...` on it and has been filtering on zero for its entire existence |
| `academic_information.Spi` has **zero writers** | Four call sites read an empty table |
| `Student.batch_id` is an FK to `Batch` (column `batch_id_id`); `Student.batch` is an unrelated integer year | Reading the wrong one is silent and plausible |
| Summer semesters stored under **even** `semester` numbers, labelled `Summer sem//2` | `(4, "Summer Semester")` and `(4, "Even Semester")` are different semesters that sort identically |
| `ResultAnnouncement.created_at` is *creation* time, not declaration time | The obvious field is the wrong field |
| `semester_type` is nullable, so the unique constraint does not dedupe NULLs on Postgres | Pre-migration rows never match a typed lookup |
| Publication requires `announced` **and** `_is_result_published_for()`, and that helper does not itself check `announced` | Every ERP call site re-ANDs it by hand; forgetting is a data leak |
| `grade_conversion` gives `F` a factor of **0.2** | F earns 2.0 points and its credit — the opposite of most people's assumption |

Additionally, `Fusion_System_Administrator` writes raw `ALTER TABLE` statements against the ERP
(`api/views/schema.py:12-52`), so production has columns no monolith migration knows about. Any shadow
model we hand-write will drift.

## Decision

**All ERP access goes through `modules/academics`, which is an anti-corruption layer.**

1. **One connection, read-only at the database level.** The `erp` alias uses the `platform_erp_ro`
   Postgres role: `SELECT` only, on a named allowlist of tables. A write attempt fails in Postgres, not in
   a code review.
2. **`managed = False` shadow models live only in `modules/academics/erp/`.** An `import-linter` contract
   forbids importing them from anywhere else. This is the same proven pattern as
   `Fusion_System_Administrator/Backend/backend/api/models/erp.py`.
3. **Shadow models are verified against `information_schema` at startup** and by a CI check, so H2-style
   column drift is caught immediately rather than at the first failing query.
4. **No other module may name an ERP concept.** Placement calls
   `academics.contracts.get_standings(user_ids)` and receives platform vocabulary — `cpi`, `semester`,
   `semester_type`, `declared_at`, `standing_version`. It never sees `Student_grades`,
   `ResultAnnouncement` or `grade_conversion`.
5. **No foreign key from any platform table to any ERP table.** Cross-database FKs are impossible in
   Django anyway; this makes it an explicit rule rather than an accident.
6. **The ACL translates the traps** — the mapping table above becomes explicit code in
   `modules/academics/erp/translate.py`, with a test per row.
7. **CPI is never recomputed.** The ACL pulls the ERP's own computed values.
   → [ADR-0008](0008-declared-academic-snapshot-for-cpi.md)

The single exception to read-only: the **IAM projector** writes three `globals_*` tables using a
different, equally narrow role (`iam_erp_projector`). That is a separate service and a separate grant, and
it is documented in
[legacy-compatibility-and-erp-projection.md](../../02-iam/legacy-compatibility-and-erp-projection.md).

## Consequences

**Good**

- ERP quirks are contained in one directory with one owner. A new developer working on Placement never
  needs to learn that `F` is worth 2.0 points.
- The platform **cannot** corrupt academic data. That is enforced by Postgres grants, which survive bad
  code, bad reviews and bad days.
- When the ERP changes a column, exactly one place breaks, and CI says so before production does.
- If the academic system is ever rewritten, the ACL is the only thing to reimplement.
- The traps become tested assertions instead of tribal knowledge.

**Bad, and accepted**

- An extra indirection for every academic read. Accepted — the alternative is the trap table above spread
  across every module.
- The ACL must be kept current with an actively-developed ERP. Mitigated by the `information_schema`
  check and the nightly snapshot reconciliation, both of which fail loudly.
- Cross-database joins are impossible, so some reads need two queries plus an in-memory join. Mitigated by
  `contracts.py` being plural-by-signature (`get_standings(user_ids)`), which makes the batched form the
  only form available.
- `modules/academics` becomes a bottleneck for academic feature work. Accepted at this team size; it is
  also small.

## Alternatives considered

**Let each module read the ERP directly.** Rejected: every module would independently rediscover that
`Student.cpi` is zero and that `F` is worth 2.0 points, and some would get it wrong. This is precisely how
the deprecated code arrived at filtering on a dead column.

**Call the legacy HTTP API instead of reading its database.** Attractive in principle — a real service
boundary. Rejected as the *primary* mechanism because the existing endpoints are unsuitable: the
admin transcript endpoints (`generate_transcript`, `generate_gradesheet_data`, `grade_validation`) **ignore
`ResultAnnouncement` entirely** and would happily serve undeclared results, `GenerateStudentResultPDFAPI`
has a live `ImportError` on its server-computed path, and the student-facing endpoint only works for the
authenticated student. We do use **one** purpose-built internal endpoint for the CPI pull
([ADR-0008](0008-declared-academic-snapshot-for-cpi.md)); everything else is direct read-only SQL through
the ACL.

**Replicate the ERP tables we need into `fusion_nonacad`.** Rejected: a second copy of academic data to
keep current, with no compensating benefit — read-only access to the same cluster is cheaper and cannot
go stale.

**Write to the ERP when convenient (e.g. update `Student.cpi` so legacy reports work).** Rejected
emphatically. Two writers for one fact is the failure mode this whole design exists to avoid, and
`Student.cpi` being dead is the ERP's business to fix, not ours.

## Verification

- A write through the `erp` alias raises `InsufficientPrivilege`. Tested against a real Postgres role.
- `import-linter` fails if `modules/academics/erp/` is imported from outside `modules/academics`.
- A CI check diffs every shadow model's fields against `information_schema.columns` and fails on drift.
- One test per row of the trap table above, asserting the ACL translates it correctly.
- A grep check fails the build if `Student.cpi` or the `Spi` model is referenced anywhere in the platform.
