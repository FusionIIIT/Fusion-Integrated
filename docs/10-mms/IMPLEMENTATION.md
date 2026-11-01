# MMS implementation coverage

This document describes the local implementation against the frozen problem statement v1.0 and the v1.4 CFR/AFR, use-case, business-rule, workflow, and traceability artifacts. The approved `README.md` in this directory is intentionally unchanged.

## Implemented

| Behavior | Current coverage | Source trace |
| --- | --- | --- |
| Module registration, permission declarations, server-side module grant, frontend `/mess` route | Django app, endpoint `HasModuleGrant("mms")` gates, role grants for student, caretaker, warden, and admin | CFR-001 to CFR-003; BR-001 to BR-007 |
| Time-limited Caretaker/Warden assignment history and immediate handoff | Admin-only assignment endpoint closes the currently active assignment and records the new employee ID and end time; operational caretaker writes also require that the caller is the active assignment | AFR-002 to AFR-006, AFR-096 to AFR-099; BR-002 to BR-007 |
| Registration and deregistration request lifecycles | Caretaker opens a cycle window; students register only while open and may request deregistration at any time while registered; caretaker decisions are recorded; approval stores next-calendar-day effect | CFR-004 to CFR-007; BR-008 to BR-013; CW-MMS-01 and CW-MMS-02 |
| Weekly menu viewing and item entry | Day/meal/item structure and student, caretaker, and warden visibility; caretaker-only entry | CFR-008; BR-014, BR-038, BR-039; UC-007 to UC-009 |
| Rebate submission and decision | Required reason, conditional “other” explanation, inclusive minimum three days, one-calendar-day lead time, overlapping-request prevention, approve/reject, and status history | CFR-011 and CFR-012; BR-019, BR-021 to BR-025; CW-MMS-03 |
| Vacation surveys and responses | Caretaker creates a survey with deadline; currently registered students are enrolled; a student may submit Yes/No once before deadline; caretaker/warden can view response summaries; a scheduled task applies No after the deadline | CFR-013 and CFR-014; BR-026, BR-027, and BR-041; CW-MMS-04 |
| Special food, feedback, announcements, operational counts | Special food request lead-time, manual approve/reject and post-approval Served/Cancelled states; text feedback; Caretaker/Warden announcements; basic MMS-only counts | CFR-015 to CFR-022; BR-020, BR-028, BR-031 to BR-034; CW-MMS-05 |

## Not implemented or deliberately incomplete

- Monthly bill generation, caretaker finalization/publication, student bill access, balance views, and rebate/special-food bill adjustments are not implemented. Daily rates and special meal charges are policy inputs; no rate or accounting behavior has been invented.
- The special-food default rejection is not implemented. The exact decision period is institution-defined; the source mentions 12 hours only as intended, so no fixed timeout is used. The model carries an optional deadline but request creation does not set it.
- Rebate date changes at approval are not exposed because they are permitted only where external mess policy allows them, and that policy is not supplied.
- Menu items can be added and viewed, but edit/delete endpoints and menu-update notifications are not implemented.
- Feedback submission and review are supported without a formal resolution workflow. Announcement publication and history are supported, but event email delivery/notification outbox work is not implemented.
- The summaries are counts only. Searchable registered-student lists, detailed rebate/survey summaries, special meal logs, and billing reports are not complete.
- No email delivery infrastructure is included. No in-app event or outbound email is emitted by this slice.
- Admin access to weekly menus remains denied. The source matrix marks Admin menu visibility as partial because the frozen problem statement conflicts with the Admin operational-data restriction; the implementation follows the stricter operational-data boundary.
- The source matrix also flags the actor allowed to record Served/Cancelled as unresolved. This implementation keeps the prior Caretaker assignment for those transitions; this requires institutional confirmation.

The matrix lists 22 CFRs, 101 AFRs, 31 use cases, and 41 active business rules. This implementation is a partial implementation and does not claim full AFR coverage.
