# Spec tests: gymkhana
Student 1 (git author name): Aman-022
Student 2 (git author name): Ayushnotafk
Design commit (hash and subject): 732e171 Freeze Gymkhana specification-based test designs (FR, BR, UC, WF)
Baseline commit (hash and subject): e3c1b78 Add gymkhana spec tests and baseline triage log
Student 1's 10/10 commit the baseline ran on (hash): 4fd66a11736f8f05c76469884f9b78bacd440aae

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | fr | 53 | 39 | 14 | 0 | 82.3% | 51.1% |
| baseline | uc | 46 | 39 | 2 | 5 | 80.1% | 48.3% |
| baseline | br | 50 | 35 | 14 | 1 | 79.7% | 47.7% |
| baseline | wf | 37 | 19 | 15 | 3 | 78.5% | 45.4% |

| q2 | fr | 53 | 39 | 14 | 0 | 82.3% | 51.1% |
| q2 | uc | 46 | 39 | 2 | 5 | 80.1% | 48.3% |
| q2 | br | 50 | 35 | 14 | 1 | 79.7% | 47.7% |
| q2 | wf | 37 | 19 | 15 | 3 | 78.5% | 45.4% |

| q3 | fr | 53 | 39 | 14 | 0 | 82.3% | 51.1% |
| q3 | uc | 46 | 39 | 2 | 5 | 80.1% | 48.3% |
| q3 | br | 50 | 35 | 14 | 1 | 79.7% | 47.7% |
| q3 | wf | 37 | 19 | 15 | 3 | 78.5% | 45.4% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with spec sentence) |
|---------|-----------|------------|----------|----------|---------------------------------------------------------------------------------|
| test_gym_afr_002_invalid_coordinator | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_002_invalid_co_coordinator | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_003_invalid | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_004_invalid | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_008_invalid_coordinator | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_008_invalid_co_coordinator | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_011_equal | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_011_reversed | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_020_unauthorized | fr | fr | Confirmed implementation defect | FAIL: assert 200 == 404
 +  where 200 = <Response status_code=200, "application/json">.status_code | Pending review |
| test_gym_afr_024_invalid | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_030_negative | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_030_missing_file | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_033 | fr | fr | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_afr_034_unassigned | fr | fr | Confirmed implementation defect | FAIL: assert 200 == 404
 +  where 200 = <Response status_code=200, "application/json">.status_code | Pending review |
| test_TC_GYM_004_UC_GYM_001_Exception_E1 | uc | uc | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: no club data storage failure interface is exposed | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_TC_GYM_009_UC_GYM_002_Exception_E1_Storage_Failure | uc | uc | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: session booking storage failure has no injectable storage interface | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_TC_GYM_010_UC_GYM_002_Exception_E1_Notification_Failure | uc | uc | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: notification processing failure cannot be induced through the available interfaces | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_TC_GYM_014_UC_GYM_003_Exception_E1_Invalid_Faculty_Reference | uc | uc | Confirmed implementation defect | FAIL: assert 201 in (400, 422)
 +  where 201 = <Response status_code=201, "application/json">.status_code | Pending review |
| test_TC_GYM_016_UC_GYM_003_Exception_E1_Storage_Failure | uc | uc | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: event storage failure has no injectable storage interface | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_TC_GYM_041_UC_GYM_010_Exception_E1_Invalid_Required_References | uc | uc | Confirmed implementation defect | FAIL: assert 201 in (400, 422)
 +  where 201 = <Response status_code=201, "application/json">.status_code | Pending review |
| test_TC_GYM_044_UC_GYM_011_Exception_E1_Update_Failure | uc | uc | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: club status update storage failure has no injectable interface | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_br_gym_001_negative_invalid_student_assignment[coordinator-1] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_001_negative_invalid_student_assignment[co_coordinator-1] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_001_negative_invalid_student_assignment[replacement-1] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_002_negative_invalid_faculty_assignment | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_003_negative_disallowed_category | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_005_invalid_booking_time_range[sessions-10:00:00-10:00:00] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_005_invalid_booking_time_range[sessions-11:00:00-10:00:00] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_005_invalid_booking_time_range[events-10:00:00-10:00:00] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_005_invalid_booking_time_range[events-11:00:00-10:00:00] | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_012_poll_requires_minimum_choices | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_014_inactive_poll_denies_participation | br | br | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: The poll model and API expose expiry but no separate active/inactive state. | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_br_gym_017_negative_budget_amount_is_rejected | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_018_budget_request_without_supporting_file_is_rejected | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_019_report_without_required_file_is_rejected | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_br_gym_020_unconfigured_venue_is_rejected | br | br | Confirmed implementation defect | FAIL: assert 400 == 422
 +  where 400 = <Response status_code=400, "application/json">.status_code | Pending review |
| test_gym_br_gym_001_001_invalid_coordinator_refused | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_student_leader","message":"Selected leader 999 must refe | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_br_gym_002_001_invalid_co_coordinator_refused | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_student_leader","message":"Selected leader 999 must refe | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_br_gym_003_001_invalid_faculty_councillor_refused | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_faculty_councillor","message":"Club Faculty Councillor 9 | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_br_gym_004_001_invalid_category_refused | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_club_category","message":"Club category must be one of T | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_br_gym_004_002_missing_required_data_refused | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"validation_error","message":"The submitted data was not valid.", | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_bw02_001 | wf | wf | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: The available Gymkhana API persists notification outbox entries, but no notification | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_gym_br_gym_012_001_poll_requires_two_choices | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"validation_error","message":"The submitted data was not valid.", | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_br_gym_012_002_poll_requires_target_groups | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"missing_poll_targets","message":"A poll must target at least one | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section62_001_booking_requires_increasing_time[session-10:00:00-10:00:00] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_booking_details","message":"Booking start time must be e | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section62_001_booking_requires_increasing_time[session-11:00:00-10:00:00] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_booking_details","message":"Booking start time must be e | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section62_001_booking_requires_increasing_time[event-10:00:00-10:00:00] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_booking_details","message":"Booking start time must be e | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section62_001_booking_requires_increasing_time[event-11:00:00-10:00:00] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_booking_details","message":"Booking start time must be e | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section61_002_invalid_leadership_change_refused | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_student_leader","message":"Selected leader 999 must refe | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section66_001_budget_amount_is_non_negative[-1.00-422-0] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"invalid_budget_amount","message":"Budget request amount must be | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section66_002_budget_requires_file_and_stores_complete_request[missing-file] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"validation_error","message":"The submitted data was not valid.", | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section67_001_report_requires_file_and_stores_complete_report[missing-file] | wf | wf | Unresolved | FAIL: AssertionError: b'{"error":{"code":"validation_error","message":"The submitted data was not valid.", | Triaged in Q2; awaiting Student 1 / Student 2 resolution |
| test_gym_section41_001_session_notification_delivered | wf | wf | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: The available Gymkhana API persists notification outbox entries, but no notification | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
| test_gym_section41_002_event_notification_delivered | wf | wf | Test-generation / test-implementation problem | SKIP: NOT_AUTOMATED: The available Gymkhana API persists notification outbox entries, but no notification | Skipped with NOT_AUTOMATED; notification delivery cannot be verified via available interfaces |
