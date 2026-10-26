# ELM coherent requirement implementation map

This is an implementation map, not a certification of complete atomic-requirement coverage. See the verification report and setup guide for limits.

| CFR | Requirement | Implementation and verification boundary |
| --- | --- | --- |
| CFR-EL-001 | Role-based ELM access | API gates tested; live IAM role grants remain to verify. |
| CFR-EL-002 | Create and submit leave application | Implemented for single-year applications. |
| CFR-EL-003 | Validate a leave request before progression | Core validation tested; cross-year requests require splitting. |
| CFR-EL-004 | CL entitlement and treatment | Entitlement and half-day handling tested. |
| CFR-EL-005 | RH entitlement and treatment | Published RH dates and quota tested. |
| CFR-EL-006 | SCL entitlement and treatment | Quota and higher-sanction workflow implemented; authority judges purpose. |
| CFR-EL-007 | EL entitlement and carry-forward | Annual credit and carry-forward implemented. |
| CFR-EL-008 | Faculty VL and VL-to-EL conversion | Conversion tested; vacation data imported rather than live service integration. |
| CFR-EL-009 | COL entitlement and treatment | Quota/evidence-reference validation; no document upload/verification. |
| CFR-EL-010 | Continuous-day counting | Continuous counting tested. |
| CFR-EL-011 | Nominate an eligible substitute | Substitute eligibility tested. |
| CFR-EL-012 | Obtain substitute response and enforce consent gate | Consent, decline recovery and replacement tested. |
| CFR-EL-013 | CL/RH Unit Head final decision | Assigned Unit Head decisions tested. |
| CFR-EL-014 | Higher-sanction progression to final decision | Configured route implemented; automatic re-resolution of pending routes is not implemented. |
| CFR-EL-015 | Director self-sanction | Director-specific route tested with active-role check. |
| CFR-EL-016 | Record and communicate final leave decision | Final decision and inbox notification implemented; external attendance synchronization remains. |
| CFR-EL-017 | No post-submission modification | No update endpoint; fresh application required. |
| CFR-EL-018 | Immediate withdrawal of pending request | Immediate terminal withdrawal tested. |
| CFR-EL-019 | Cancel approved leave before start | Separate pre-start cancellation tested. |
| CFR-EL-020 | Extend ongoing EL/COL/VL | Incremental extension tested; cross-year extension rejected. |
| CFR-EL-021 | Review resumption and adjust actual leave where required | Early/normal/late review tested; external attendance consumer remains. |
| CFR-EL-022 | View leave balances and history | Balances, history and account API implemented. |
| CFR-EL-023 | Obtain printable/exportable leave application | Owner-only printable HTML export tested. |
| CFR-EL-024 | Maintain policy parameters and hierarchy configuration | Configuration APIs; no dedicated admin screens or retroactive credit rewrite. |
| CFR-EL-025 | Maintain and publish holiday/RH calendar | Draft/new published calendars via API; no dedicated admin screens. |
| CFR-EL-026 | Maintain authorized leave records | Conservative audit-annotation maintenance only. |
| CFR-EL-027 | Record already-sanctioned offline leave | Retrospective synchronization API with references; no admin screen. |
| CFR-EL-028 | Execute and record year-end leave-account processing | Idempotent calendar-year command; scheduling and historical/post-close handling remain. |
| CFR-EL-029 | Configure workflow-task SLA thresholds | Global reminder/escalation thresholds via API; task-class-specific thresholds not implemented. |
| CFR-EL-030 | Notify a user when an actionable task is assigned | In-app assignment notification implemented. |
| CFR-EL-031 | Remind on a still-pending SLA task | Pending-only reminders tested. |
| CFR-EL-032 | Escalate a still-pending SLA task | Pending-only notification escalation tested; no automatic reassignment. |
