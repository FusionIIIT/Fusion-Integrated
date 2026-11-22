# Spec tests: visitor_hostel

Student 1 (git author name): Aksh Wadhawan  
Student 2 (git author name): Abhay Kumar Singh  
Design commit (hash and subject): 4f1a29c Freeze spec test design for visitor_hostel (FR, BR, UC, WF)  
Baseline commit (hash and subject): 8e7d21b Baseline spec test suite run for visitor_hostel  
Student 1's 10/10 commit the baseline ran on (hash): 7e4e782 22A Mobile Frontend Assignment 7: Visitors Hostel module implementation  

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| baseline | fr | 33 | 0 | 33 | 0 | 33.0% | 20.0% |
| baseline | br | 18 | 0 | 18 | 0 | 45.0% | 30.0% |
| baseline | uc | 30 | 0 | 30 | 0 | 40.0% | 25.0% |
| baseline | wf | 6 | 0 | 6 | 0 | 38.0% | 22.0% |
| final (Q2) | fr | 34 | 34 | 0 | 0 | 95.9% | 90.5% |
| final (Q2) | br | 32 | 32 | 0 | 0 | 94.3% | 91.2% |
| final (Q2) | uc | 2 | 2 | 0 | 0 | 93.8% | 89.4% |
| final (Q2) | wf | 12 | 12 | 0 | 0 | 95.1% | 92.0% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|:---:|
| FR-001 | AFR-VH-001 | FR | Confirmed implementation defect | IAMPrincipal backend attribute access error during login | Fixed in views and auth scoping; verified by `test_online_submission_uses_iam_id` | No |
| FR-002 | AFR-VH-002 | FR | Confirmed implementation defect | Foreign indenter could see booking details | Scoped queryset by `indenter_id == user_id`; verified by `test_other_indenter_cannot_access_booking` | No |
| FR-004 | AFR-VH-004 | FR | Confirmed implementation defect | Indenter could execute staff action endpoints | Added `HasHostelRole` permission checks; verified by `test_indenter_cannot_execute_staff_actions` | No |
| FR-005 | AFR-VH-005 | FR | Confirmed implementation defect | Principal `is_staff` check failed on IAM session | Converted staff checks to module/action role grants; verified by `test_list_scoped_to_owner` | No |
| FR-007 | AFR-VH-007 | FR | Confirmed implementation defect | Mass-assignment allowed spoofing status and indenter_id | Fields marked `read_only` on serializer; verified by `test_workflow_fields_cannot_be_mass_assigned` | No |
| FR-008 | AFR-VH-008 | FR | Confirmed implementation defect | Invalid date and negative room count accepted | Added model and serializer validation; verified by `test_invalid_requisitions_rejected` | No |
| FR-009 | AFR-VH-009 | FR | Confirmed implementation defect | Planned check-in/out times not saved | Added `check_in_time` and `check_out_time` fields; verified by `test_planned_times_and_occupants_persist` | No |
| FR-011 | AFR-VH-011 | FR | Confirmed implementation defect | Offline booking accessible to plain indenter | Restricted offline submission to `vh_caretaker`; verified by `test_offline_booking_is_caretaker_only` | No |
| BR-004 | BR-VH-004 | BR | Confirmed implementation defect | Caretaker could forward booking without room availability | Added room availability check in forward routing; verified by `test_forward_requires_available_capacity` | No |
| BR-009 | BR-VH-009 | BR | Confirmed implementation defect | No-show did not compute 50% tariff penalty | Implemented no-show penalty in billing service; verified by `test_no_show_charge_uses_half_one_day_rent` | No |
| BR-011 | BR-VH-011 | BR | Confirmed implementation defect | Cancellation charge calculation omitted lead-time boundaries | Implemented 3-tier boundary service; verified by `test_cancellation_boundaries` | No |
| BR-023 | BR-VH-023 | BR | Confirmed implementation defect | Tariff lookup used future modified rates | Scoped tariff lookup to `effective_from <= check_in_date`; verified by `test_tariff_effective_on_arrival_not_future` | No |
| BR-024 | BR-VH-024 | BR | Confirmed implementation defect | Meal orders permitted for un-checked-in bookings | Restricted meal ordering to active `checked_in` stays; verified by `test_meals_only_for_current_residents` | No |
| BR-031 | BR-VH-031 | BR | Confirmed implementation defect | Partial checkout state persisted without tariff | Wrapped checkout in `@transaction.atomic`; verified by `test_checkout_without_tariff_is_atomic` | No |
| BR-035 | BR-VH-035 | BR | Confirmed implementation defect | Bill amount was mutable after generation | Enforced bill immutability; verified by `test_bill_survives_tariff_change_and_checkout_retry` | No |
| BR-041 | BR-VH-041 | BR | Confirmed implementation defect | Inventory threshold alert used `<=` instead of `<` | Changed comparison to strict less-than; verified by `test_inventory_threshold_is_strict` | No |
| WF-01 | BW-VH-01 | WF | Confirmed implementation defect | In-charge could approve before caretaker forwarding | Enforced strict two-stage sequencing; verified by `test_approval_requires_caretaker_then_in_charge` | No |
| WF-03 | BW-VH-03 | WF | Confirmed implementation defect | Rejection allowed empty reason | Mandated non-empty reason; verified by `test_rejection_requires_reason` | No |
| WF-04 | BW-VH-04 | WF | Confirmed implementation defect | Malformed room allotment list did not rollback | Added atomic allotment validation; verified by `test_bad_room_allotment_is_atomic` | No |
| WF-05 | BW-VH-05 | WF | Confirmed implementation defect | Room double-booking allowed on concurrent requests | Added `select_for_update` row locks; verified by `test_allotment_conflict_and_cancellation_release` | No |
| WF-08 | BW-VH-08 | WF | Confirmed implementation defect | Room under maintenance was allotable | Added check on room status; verified by `test_maintenance_room_cannot_be_allotted` | No |
| UC-001 | UC-VH-001 | UC | Confirmed implementation defect | Cash settlement did not record receipt number or audit | Added settlement receipt logging and audit event; verified by `test_booking_to_stay_meal_checkout_and_cash_settlement` | No |
| UC-008 | UC-VH-008 | UC | Confirmed implementation defect | Caretaker could self-approve inventory replenishment | Restriced replenishment approval to `vh_in_charge`; verified by `test_inventory_request_needs_in_charge_approval` | No |

