# Application state machine

Generated from `modules/placement/domain/state_machine.py` by `ops/docs/placement_reference.py`. Do not edit by hand.
Every status change goes through `services/applications.transition` or the offer services, which resolve the move against this table first, so a move not listed here cannot happen.
The spec's states map as follows: Applied is `submitted`, Shortlisted is `shortlisted`, Interview Scheduled is `interview_scheduled`, Offer Extended is `offer_issued`, Offer Accepted is `offer_accepted`, Offer Rejected is `offer_declined` (CW-PC-04).

Terminal states: `auto_withdrawn`, `offer_accepted`, `offer_declined`, `offer_expired`, `rejected`, `withdrawn`.

| From | To | Who may | Permission | Guards |
|---|---|---|---|---|
| `draft` | `submitted` | student | `placement.application.create` | window_open, profile_complete, is_eligible, may_apply |
| `submitted` | `under_review` | recruiter, staff | `placement.application.review` | — |
| `submitted` | `shortlisted` | recruiter, staff | `placement.application.review` | — |
| `submitted` | `rejected` | recruiter, staff | `placement.application.review` | has_reason |
| `under_review` | `shortlisted` | recruiter, staff | `placement.application.review` | — |
| `under_review` | `rejected` | recruiter, staff | `placement.application.review` | has_reason |
| `shortlisted` | `rejected` | recruiter, staff | `placement.application.review` | has_reason |
| `shortlisted` | `interview_scheduled` | recruiter, staff | `placement.interview.create` | has_scheduled_round |
| `interview_scheduled` | `selected` | recruiter, staff | `placement.application.review` | — |
| `interview_scheduled` | `rejected` | recruiter, staff | `placement.application.review` | has_reason |
| `interview_scheduled` | `shortlisted` | recruiter, staff | `placement.application.review` | — |
| `selected` | `offer_issued` | recruiter, staff | `placement.offer.create` | company_authorized |
| `shortlisted` | `offer_issued` | recruiter, staff | `placement.offer.create` | company_authorized |
| `interview_scheduled` | `offer_issued` | recruiter, staff | `placement.offer.create` | company_authorized |
| `offer_issued` | `offer_accepted` | student | `placement.offer_response.create` | offer_window_open, policy_allows_accept |
| `offer_issued` | `offer_declined` | student | `placement.offer_response.create` | offer_window_open |
| `offer_issued` | `offer_expired` | system | `placement.offer_expiry.create` | offer_window_closed |
| `offer_issued` | `rejected` | staff | `placement.offer.revoke` | has_reason |
| `draft` | `withdrawn` | student | `placement.application.delete` | — |
| `submitted` | `withdrawn` | student | `placement.application.delete` | — |
| `under_review` | `withdrawn` | student | `placement.application.delete` | — |
| `shortlisted` | `withdrawn` | student | `placement.application.delete` | — |
| `interview_scheduled` | `withdrawn` | student | `placement.application.delete` | — |
| `selected` | `withdrawn` | student | `placement.application.delete` | — |
| `offer_issued` | `withdrawn` | student | `placement.application.delete` | — |
| `draft` | `auto_withdrawn` | system | `placement.application.revoke` | — |
| `submitted` | `auto_withdrawn` | system | `placement.application.revoke` | — |
| `under_review` | `auto_withdrawn` | system | `placement.application.revoke` | — |
| `shortlisted` | `auto_withdrawn` | system | `placement.application.revoke` | — |
| `interview_scheduled` | `auto_withdrawn` | system | `placement.application.revoke` | — |
| `selected` | `auto_withdrawn` | system | `placement.application.revoke` | — |
| `offer_issued` | `auto_withdrawn` | system | `placement.application.revoke` | — |
