# Complaint Management System (CMS) — Implementation Reference

This document provides bidirectional traceability between all specification identifiers
and concrete code implementations in `modules/complaints/`.

## 1. Consolidated Requirements (CFRs)
- `CFR-001` Intake & Validation: [`modules/complaints/services/complaints.py:submit_complaint`](../../modules/complaints/services/complaints.py)
- `CFR-002` Assignment & Routing: [`modules/complaints/services/complaints.py:assign_complaint`](../../modules/complaints/services/complaints.py)
- `CFR-003` In-Progress Updates: [`modules/complaints/services/complaints.py:progress_complaint`](../../modules/complaints/services/complaints.py)
- `CFR-004` Resolution Recording: [`modules/complaints/services/complaints.py:resolve_complaint`](../../modules/complaints/services/complaints.py)
- `CFR-005` Rejection Workflow: [`modules/complaints/services/complaints.py:reject_complaint`](../../modules/complaints/services/complaints.py)
- `CFR-006` Verified Closure: [`modules/complaints/services/complaints.py:verify_closure`](../../modules/complaints/services/complaints.py)
- `CFR-007` Reopening Request: [`modules/complaints/services/complaints.py:request_reopen`](../../modules/complaints/services/complaints.py)
- `CFR-008` Reopening Review: [`modules/complaints/services/complaints.py:review_reopen`](../../modules/complaints/services/complaints.py)
- `CFR-009` Manual Escalation: [`modules/complaints/services/complaints.py:escalate_complaint`](../../modules/complaints/services/complaints.py)
- `CFR-010` Automatic SLA Breach Escalation: [`modules/complaints/services/complaints.py:check_and_escalate_sla_breaches`](../../modules/complaints/services/complaints.py)
- `CFR-011` Post-Closure Feedback: [`modules/complaints/services/complaints.py:submit_feedback`](../../modules/complaints/services/complaints.py)
- `CFR-012` 75% SLA Reminder: [`modules/complaints/services/complaints.py:check_and_send_sla_reminders`](../../modules/complaints/services/complaints.py)

## 2. Business Rules (BRs)
- `BR-001` Handler Assignment Restrictions: [`modules/complaints/domain/state_machine.py`](../../modules/complaints/domain/state_machine.py)
- `BR-002` Supervisor Delegation: [`modules/complaints/services/complaints.py`](../../modules/complaints/services/complaints.py)
- `BR-003` Active Category Validation: [`modules/complaints/services/complaints.py`](../../modules/complaints/services/complaints.py)
- `BR-004` Rejection Reason Mandatory: [`modules/complaints/api/serializers.py`](../../modules/complaints/api/serializers.py)
- `BR-005` Feedback Uniqueness & 1-5 Bounds: [`modules/complaints/models.py`](../../modules/complaints/models.py)
- `BR-006` Single Manual Escalation Limit: [`modules/complaints/services/complaints.py`](../../modules/complaints/services/complaints.py)
- `BR-007` SLA Automatic Escalation: [`modules/complaints/services/complaints.py`](../../modules/complaints/services/complaints.py)
- `BR-008` Zero Cross-Module Foreign Keys: [`modules/complaints/models.py`](../../modules/complaints/models.py)
- `BR-009` Standardized Complaint ID Format: [`modules/complaints/models.py`](../../modules/complaints/models.py)
