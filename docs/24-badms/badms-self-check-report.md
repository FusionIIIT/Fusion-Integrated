# BADMS Blueprint Self-Check & Verification Report (Final Revision)

**Module:** Backup and Database Archive Management System (BADMS)  
**Module Code:** `badms`  
**Target Blueprint:** `docs/24-badms/badms-blueprint.md`  
**Governing Prompt:** `docs/08-delivery/new-module-prompt.md`  
**Specification Source:** `/Users/trupesha/Desktop/drive-download-20261101T110138Z-1-001`  
**Environment:** `module-only`

---

## 1. Traceability & ID Coverage Check
- **Composite Functional Requirements (CFRs):** 19 of 19 accounted for (`CFR-BA-001` through `CFR-BA-019`).
- **Atomic Functional Requirements (AFRs):** 66 of 66 active requirements accounted for (`AFR-BA-001` through `AFR-BA-068`).
  - *Note on numbering gap:* The source specification document `02_BA_Requirement_Registry_v1.1_FINAL.docx` jumps from `AFR-BA-043` directly to `AFR-BA-045`, and from `AFR-BA-049` to `AFR-BA-051`. Zero retired or deprecated IDs exist in the specification suite. All 66 live AFRs are traced without synthetic placeholders.
- **Use Cases (UCs):** 23 of 23 accounted for (`BA-UC-001` through `BA-UC-023`).
- **Business Rules (BRs):** 21 of 21 accounted for (`BR-BA-001` through `BR-BA-021`).
- **Workflows:** 10 of 10 accounted for:
  - 7 Basis Workflows: `BW-BA-01` through `BW-BA-07`
  - 3 Composite Workflows: `CW-BA-01` through `CW-BA-03`
- **Result:** PASSED. Every specification ID is traced to an architecture layer, planned enforcement point, and design note.

---

## 2. Final Verification of Review Corrections

### 1. Production Designation for BR-BA-015 (IAM Verification Evidence)
- **Investigation & Evidence:**
  - Audited `Fusion_System_Administrator/Backend/backend/iam/rbac.py` (`CATALOGUE`) and `globals_designation`.
  - Found `Director` (`("Director", "Director", IamRole.OFFICE, FACULTY_ONLY)`).
  - The designation `Director of IT` **does not exist** anywhere in the IAM catalogue or ERP fixtures.
  - `Director` and `Director of IT` are **not interchangeable**; `Director` is the academic/executive head of the institute, while `Director of IT` is an administrative officer specified in `BR-BA-015`.
- **Resolution in Blueprint:**
  - Blueprint strictly records `Director of IT` as the specified escalation designation.
  - In development and test fixtures (`module-only`), `Director of IT` is provisioned using `manage.py assign_role` in `Fusion_System_Administrator`, or isolated to mock test notification recipients.
  - Adding `Director of IT` to the production ERP is documented as an external administrative prerequisite for the academic office.

### 2. Status of the 10 GB Storage Quota Baseline
- **Correction:** The 10 GB baseline is explicitly documented as a **proposed default pending approver approval**.
- It is not presented as an approved institute policy or final specification requirement. The model and contracts allow configuring the initial baseline via `SecurityPolicy` once approved.

### 3. Scheduler Catch-Up & De-Duplication Protocol (BR-BA-011, AFR-BA-006)
- **Correction:** The scheduled backup dispatcher (`badms.tasks.evaluate_and_dispatch_due_backups`) runs every minute.
- **Downtime Catch-Up & Delayed Execution:**
  - When recovering from downtime (`now > next_run_at`), the task executes exactly one catch-up backup for the missed period.
  - Concurrency lock (`select_for_update`) on the active `BackupSchedule` record prevents concurrent Celery workers from executing duplicate backups.
  - Immediately updates `last_run_at = now` and recalculates `next_run_at` to the next future scheduled occurrence using `croniter`.
  - Pre-backup repository reachability checks (`BR-BA-013`) and post-dump SHA-256 checksum verification are strictly enforced.

### 4. Backup Failure Alert SLA (BR-BA-014)
- **Correction:** To guarantee the 5-minute SLA is never violated by periodic Celery task boundary timing, backup failure alerting is **event-driven and dispatched immediately in-band** when `services/backups.py` records a failure.
- A Celery task running every 1 minute acts as an operational safety net for unnotified failures.

### 5. Policy-Governed Archive Purge (BR-BA-008, AFR-BA-056)
- **Correction:** Celery task `purge_expired_archives` does not introduce unauthorized automatic physical file deletion.
- Archives exceeding retention duration transition to `retention_expired` and are queued for purge review. Actual physical deletion executes only after explicit administrative authorization or when automated purge is explicitly enabled in `SecurityPolicy`.

---

## 3. Remaining Approval Decisions for Independent Approver Sign-Off

1. **Designation Provisioning in Dev Environment:**
   - Confirm provisioning of `"HOD"`, `"SysAdmin"`, `"Super Admin"`, `"IT Security"`, and `"Director of IT"` in `globals_designation` using `Fusion_System_Administrator`'s `manage.py assign_role`.
2. **Default Baseline Storage Quota Value:**
   - Formal sign-off on the proposed default baseline quota value (e.g., 10 GB) or specification of the institute's preferred default for uninitialized users.
3. **Automated vs. Manual Purge for Retention-Expired Archives:**
   - Confirm whether retention-expired archives should default to requiring manual administrative purge authorization, or whether automated deletion may be enabled via `SecurityPolicy`.
