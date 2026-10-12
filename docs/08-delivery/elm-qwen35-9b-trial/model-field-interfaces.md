LeavePolicy: CL_DAYS, RH_DAYS, SCL_MAX_DAYS, EL_DAYS, COL_DAYS, VL_DAYS, VL_TO_EL_RATIO
HolidayCalendar: year, is_effective, created_by_user_id
Holiday: calendar, date, type, name
VacationPeriod: year, start_date, end_date, name
OrganizationalUnit: code, name, parent_unit_id, unit_head_user_id
LeaveHierarchy: name, description
LeaveHierarchyStep: hierarchy, order, role_code, is_establishment_step
LeaveApplication: STATUS_CHOICES, category, user_id, start_date, end_date, purpose, station_leave_required, station_leave_details, substitute_user_id, substitute_consent_given, status, unit_head_user_id, hierarchy_step_order, final_decision_user_id, final_decision_date, final_decision_type, original_application_id, extension_incremental_days, actual_resumption_date, resumption_type, created_by_user_id, updated_by_user_id, submitted_by_user_id, withdrawn_by_user_id, cancelled_by_user_id
LeaveBalance: user_id, effective_date, cl_balance, rh_balance, scl_balance, el_balance, col_balance, vl_balance
LeaveTransaction: TRANSACTION_TYPE_CHOICES, application, user_id, transaction_type, category, quantity, balance_before, balance_after, reference_application_id, reference_transaction_id, processed_by_user_id, processed_at
WorkflowTask: TASK_TYPE_CHOICES, application, task_type, assigned_to_user_id, role_code, status, reminder_threshold_seconds, escalation_threshold_seconds, last_reminder_sent_at, last_escalation_sent_at, completed_at, completed_by_user_id
SLAEventLog: EVENT_TYPE_CHOICES, task, event_type, triggered_at, threshold_seconds, message
ResumptionRecord: application, user_id, actual_resumption_date, resumption_type, reviewed_by_user_id, reviewed_at, balance_adjustment
