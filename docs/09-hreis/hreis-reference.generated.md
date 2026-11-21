# HR-EIS implementation reference

Deterministic generated documentation from the local source registry.
Run python ops/docs/hreis_reference.py after changing HR-EIS routes,
permissions or workflow edges. The script never supplies institutional
policy defaults.

## Declared permissions

| Permission | Purpose |
|---|---|
| hreis.service_record.view | View scoped HR service records |
| hreis.service_record.create | Create official employee service records |
| hreis.service_record.update | Maintain official employee service records |
| hreis.request.view | View scoped HR requests |
| hreis.approval.view | Open the assigned HR-EIS approval queue |
| hreis.leave.create | Submit own leave requests |
| hreis.balance.manage | Record verified, audited employee leave credits |
| hreis.leave.approve | Approve or reject assigned leave requests |
| hreis.appraisal.create | Submit own appraisal |
| hreis.appraisal.assign | Assign appraisal reviewers |
| hreis.appraisal.approve | Finalize assigned appraisals |
| hreis.claim.create | Submit own LTC/CPDA claims |
| hreis.claim.review | HR verify LTC/CPDA documentation and eligibility |
| hreis.claim.approve | Approve assigned LTC/CPDA claims |
| hreis.finance.review | Verify financial correctness of approved LTC/CPDA claims |
| hreis.finance.update | Record externally reported LTC/CPDA processing status |
| hreis.policy.view | Read effective HR policy |
| hreis.policy.manage | Create effective-dated HR policy |
| hreis.audit.view | Review restricted HR compliance trail |
| hreis.notification.view | Read own HR-EIS notifications |
| hreis.notification.publish | System generate HR notifications |

## Registered role grants (not proof of live IAM provisioning)

| Designation | Permissions |
|---|---|
| faculty | hreis.service_record.view, hreis.request.view, hreis.leave.create, hreis.appraisal.create, hreis.claim.create, hreis.notification.view |
| staff | hreis.service_record.view, hreis.request.view, hreis.leave.create, hreis.appraisal.create, hreis.claim.create, hreis.notification.view |
| hradmin | hreis.service_record.view, hreis.service_record.create, hreis.service_record.update, hreis.balance.manage, hreis.request.view, hreis.appraisal.assign, hreis.claim.review, hreis.policy.view, hreis.policy.manage, hreis.audit.view, hreis.notification.view |
| Accounts Admin | hreis.finance.review, hreis.finance.update, hreis.request.view, hreis.service_record.view, hreis.notification.view |
| HOD (CSE) | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| HOD (Design) | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| HOD (ECE) | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| HOD (Liberal Arts) | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| HOD (ME) | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| HOD (NS) | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| Registrar | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |
| Director | hreis.service_record.view, hreis.request.view, hreis.approval.view, hreis.leave.approve, hreis.appraisal.approve, hreis.claim.approve, hreis.notification.view |

The Accounts Admin finance designation is provisionally mapped
from the HR specification's Accountant actor and must be
confirmed by the institution before production grants.

## Navigation and guarded pages

| URL | Permission |
|---|---|
| /hreis/my-record | hreis.service_record.view |
| /hreis/requests | hreis.request.view |
| /hreis/leave | hreis.leave.create |
| /hreis/claims | hreis.claim.create |
| /hreis/appraisals | hreis.appraisal.create |
| /hreis/approvals | hreis.approval.view |
| /hreis/finance | hreis.finance.review |
| /hreis/administration | hreis.service_record.update |
| /hreis/notifications | hreis.notification.view |
| /hreis/audit | hreis.audit.view |

## Canonical state transitions

| Family | Source state | Event | Target state | Actor | Required guards | Spec |
|---|---|---|---|---|---|---|
| leave | draft | submit | pending_authority | employee | supported_leave_type, required_fields, balance_valid, eligibility_valid, route_configured | CW-HR-01 |
| leave | pending_authority | approve | approved | approving_authority | current_authority, balance_valid | BW-HR-01 |
| leave | pending_authority | reject | rejected | approving_authority | current_authority | BW-HR-02 |
| leave | pending_authority | forward | pending_authority | approving_authority | current_authority, next_authority_exists | BW-HR-03 |
| appraisal | not_submitted | submit | submitted | employee | submission_window_open | CW-HR-02 |
| appraisal | submitted | assign_reviewers | pending_review | hr_administrator | reviewers_assigned | CW-HR-02 |
| appraisal | pending_review | forward | pending_next_appraisal_authority | approving_authority | current_authority, not_final_authority | BW-HR-05 |
| appraisal | pending_review | finalize | finalized | approving_authority | current_authority, final_authority | BW-HR-04 |
| appraisal | pending_next_appraisal_authority | forward | pending_next_appraisal_authority | approving_authority | current_authority, not_final_authority | BW-HR-05 |
| appraisal | pending_next_appraisal_authority | finalize | finalized | approving_authority | current_authority, final_authority | BW-HR-05 |
| ltc | draft | submit | awaiting_hr_verification | employee | prescribed_form_present | CW-HR-03 |
| ltc | awaiting_hr_verification | verify | pending_authority | hr_administrator | documents_verified, eligibility_verified, route_configured | CW-HR-03 |
| ltc | pending_authority | approve | approved | approving_authority | current_authority | BW-HR-06 |
| ltc | pending_authority | reject | rejected | approving_authority | current_authority | BW-HR-08 |
| ltc | pending_authority | forward | pending_authority | approving_authority | current_authority, next_authority_exists | BW-HR-09 |
| ltc | approved | record_financial_processing | financial_processing_recorded | accountant | financial_correctness_verified, processing_status_recorded | CW-HR-03 |
| cpda | draft | submit | awaiting_hr_verification | employee | purpose_present, amount_present, documents_present | CW-HR-04 |
| cpda | awaiting_hr_verification | verify | pending_authority | hr_administrator | verification_passed, route_configured | CW-HR-04 |
| cpda | pending_authority | approve | approved | approving_authority | current_authority | BW-HR-10 |
| cpda | pending_authority | reject | rejected | approving_authority | current_authority | BW-HR-12 |
| cpda | pending_authority | forward | pending_authority | approving_authority | current_authority, next_authority_exists | BW-HR-13 |
| cpda | approved | record_financial_processing | financial_processing_recorded | accountant | financial_correctness_verified, disbursement_details_recorded | CW-HR-04 |

## Operational constraints

- Live policy versions are imported only from explicit institutional JSON
  via the authenticated hreis_import_policies management command or HTTP.
- Employee leave credits require a verified evidence reference.
- Payroll/finance payment statuses are recorded locally with
  immutable provenance, not bank or payroll execution.
- External provider synchronization and institutional role mapping
  remain deployment prerequisites.
- The source RTM mentions returned LTC requests but the canonical
  workflow contains no defined return event; no such state is invented.
