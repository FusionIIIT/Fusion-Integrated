"""Synthetic examples make each public operation reviewable without institutional defaults."""

from copy import deepcopy

from drf_spectacular.utils import OpenApiExample

AT = "2026-11-22T10:00:00+05:30"
RECORD = {
    "id": 1,
    "user_id": 10,
    "appointment_details": {"date": "2026-01-01"},
    "department": "CSE",
    "designation_snapshot": "Synthetic Professor",
    "service_history": [],
    "retirement_status": "",
    "revision": 1,
    "leave_balances": {"Casual": "3.0000"},
    "updated_at": AT,
}
REQUEST = {
    "id": 7,
    "user_id": 10,
    "family": "leave",
    "subtype": "Casual",
    "state": "pending_authority",
    "payload": {"duration": "1", "justification": "Synthetic leave request"},
    "claim_summary": None,
    "appraisal_summary": None,
    "route_step": 0,
    "route_total_steps": 1,
    "submitted_at": AT,
    "created_at": AT,
    "updated_at": AT,
}
POLICY = {
    "family": "leave",
    "version": 1,
    "effective_from": AT,
    "effective_until": None,
    "parameters": {
        "eligibility": {"faculty": {"Casual": True}},
        "routes": [{"employee_kind": "faculty", "department": "CSE", "authorities": ["Registrar"]}],
    },
}
CREDIT = {
    "user_id": 10,
    "leave_type": "Casual",
    "quantity": "3.0000",
    "evidence_reference": "SYNTHETIC-REGISTER",
}
NOTICE = {
    "id": 9,
    "title": "LEAVE request submitted",
    "message": "Your HR request was recorded.",
    "request_id": 7,
    "created_at": AT,
    "read_at": AT,
}
INPUTS = {
    "RecordCreateSerializer": {
        key: RECORD[key]
        for key in (
            "user_id",
            "appointment_details",
            "department",
            "designation_snapshot",
            "service_history",
        )
    },
    "RecordUpdateSerializer": {"expected_revision": 1, "department": "ECE"},
    "ReviewerAssignmentSerializer": {"reviewer_user_ids": [21]},
    "AppraisalDecisionSerializer": {"event": "finalize"},
    "ClaimReviewSerializer": {
        "document_review_reference": "SYNTHETIC-REVIEW",
        "eligibility_basis": "Manually checked institutional evidence",
    },
    "FinancialReviewSerializer": {"financial_review_reference": "SYNTHETIC-FINANCIAL-REVIEW"},
    "FinancialProcessingSerializer": {
        "financial_review_reference": "SYNTHETIC-FINANCIAL-REVIEW",
        "source_system": "finance",
        "external_status_reference": "SYNTHETIC-REPORT",
        "payment_status": "payment_pending",
    },
    "DecisionSerializer": {"event": "reject", "reason": "Supply the missing signed evidence."},
    "VerifiedLeaveCreditSerializer": CREDIT,
    "LeaveSubmitSerializer": {
        "leave_type": "Casual",
        "duration": "1",
        "justification": "Synthetic leave request",
    },
    "ClaimSubmitSerializer": {
        "family": "ltc",
        "subtype": "advance",
        "prescribed_form_reference": "SYNTHETIC-LTC-FORM",
    },
    "AppraisalSubmitSerializer": {
        "period_key": "FY2026",
        "submitted_form": {"summary": "Synthetic teaching activity"},
    },
    "PolicyCreateSerializer": POLICY,
}
OUTPUTS = {
    "RecordReadSerializer": RECORD,
    "RequestReadSerializer": REQUEST,
    "RequestDetailReadSerializer": {
        **REQUEST,
        "history": [
            {
                "source": "draft",
                "event": "submit",
                "target": "pending_authority",
                "acting_designation": "faculty",
                "reason": "",
                "recorded_at": AT,
            }
        ],
    },
    "FinancialReviewReadSerializer": {
        "request_id": 7,
        "financial_review_reference": "SYNTHETIC-FINANCIAL-REVIEW",
        "reviewed_by_user_id": 200,
    },
    "VerifiedLeaveCreditReadSerializer": {
        "id": 1,
        "user_id": 10,
        "leave_type": "Casual",
        "quantity": "3.0000",
        "recorded_at": AT,
    },
    "PolicyReadSerializer": {
        **POLICY,
        "id": 1,
        "approved_by_user_id": 99,
        "approved_designation": "hradmin",
        "recorded_at": AT,
    },
    "ComplianceRequestSerializer": {
        key: REQUEST[key]
        for key in ("id", "user_id", "family", "state", "created_at", "submitted_at")
    },
    "MyLeaveBalancesSerializer": {"user_id": 10, "leave_balances": {"Casual": "3.0000"}},
    "NotificationReadSerializer": NOTICE,
    "AuditReadSerializer": {
        "id": 1,
        "actor_user_id": 99,
        "acting_designation": "hradmin",
        "subject_user_id": 10,
        "action": "create",
        "resource_kind": "service_record",
        "resource_id": 1,
        "data": {"revision": 1},
        "recorded_at": AT,
    },
}


def _claim_example(response, operation):
    if any(word in operation for word in ("Claim", "Financial")):
        response.update(
            family="ltc",
            subtype="advance",
            payload={"prescribed_form_reference": "SYNTHETIC-LTC-FORM"},
            claim_summary={
                "purpose": "",
                "amount": None,
                "prescribed_form_reference": "SYNTHETIC-LTC-FORM",
                "hr_verified": True,
                "financial_verified": "Financial" in operation,
                "payment_status": "payment_pending" if "Financial" in operation else None,
                "status_history": [],
            },
        )
    if "FinancialProcessing" in operation:
        response["state"] = "financial_processing_recorded"
        response["claim_summary"]["status_history"] = [
            {
                "source_system": "finance",
                "external_status_reference": "SYNTHETIC-REPORT",
                "payment_status": "payment_pending",
                "recorded_at": AT,
            }
        ]
    if "ClaimSubmit" in operation:
        response["state"] = "awaiting_hr_verification"
        response["claim_summary"]["hr_verified"] = False


def _appraisal_example(response, operation):
    if "Appraisal" in operation or "ReviewerAssignment" in operation:
        response.update(
            family="appraisal",
            subtype="",
            state=(
                "finalized"
                if "AppraisalDecision" in operation
                else "pending_review"
                if "ReviewerAssignment" in operation
                else "submitted"
            ),
            payload={"period_key": "FY2026"},
            appraisal_summary={
                "period_key": "FY2026",
                "submitted_form": {"summary": "Synthetic teaching activity"},
                "reviewer_user_ids": [] if "AppraisalSubmit" in operation else [21],
            },
        )


def operation_examples(request_name, response_name, operation):
    response = deepcopy(OUTPUTS[response_name])
    if response_name == "RequestReadSerializer":
        _claim_example(response, operation)
        _appraisal_example(response, operation)
        if operation == "RequestDecisionView":
            response["state"] = "rejected"
    examples = [OpenApiExample("Synthetic response", value=response, response_only=True)]
    if request_name:
        examples.append(
            OpenApiExample("Synthetic request", value=INPUTS[request_name], request_only=True)
        )
    if request_name == "FinancialProcessingSerializer":
        examples.append(
            OpenApiExample(
                "External status unavailable",
                request_only=True,
                value={"financial_review_reference": "SYNTHETIC-FINANCIAL-REVIEW"},
            )
        )
    return examples
