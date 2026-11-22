"""Anomaly and Audit Observation lifecycle tests."""

import pytest

from modules.iaa.models import (
    AnomalyStatus,
    AuditObservationStatus,
)
from modules.iaa.services.anomalies import (
    create_anomaly,
    resolve_or_escalate_anomaly,
)
from modules.iaa.services.audit import (
    raise_audit_observation,
    respond_to_audit_observation,
    review_and_close_observation,
)

pytestmark = pytest.mark.django_db


def test_anomaly_lifecycle_escalate_and_resolve():
    anomaly = create_anomaly(
        category="duplicate_bill",
        description="Invoice #442 appears twice",
        reference_type="request",
        reference_id=12,
        flagged_by_id=3001,
        flagged_by_role="finance_staff",
    )
    assert anomaly.status == AnomalyStatus.OPEN

    escalated = resolve_or_escalate_anomaly(
        anomaly_id=anomaly.id,
        actor_id=3001,
        actor_role="finance_staff",
        action="escalate",
        remarks="Escalating to internal audit",
    )
    assert escalated.status == AnomalyStatus.ESCALATED

    resolved = resolve_or_escalate_anomaly(
        anomaly_id=anomaly.id,
        actor_id=6001,
        actor_role="audit_officer",
        action="resolve",
        remarks="Vendor confirmed corrected credit note",
    )
    assert resolved.status == AnomalyStatus.RESOLVED
    assert resolved.resolved_by_id == 6001


def test_audit_observation_unsatisfactory_loop_and_closure():
    obs = raise_audit_observation(
        auditor_id=6001,
        acting_role="audit_officer",
        department="Mechanical Engineering",
        title="Physical asset verification discrepancy",
        description="Missing asset tag on spectrometer",
        reference_type="request",
        reference_id=45,
    )
    assert obs.status == AuditObservationStatus.OPEN

    responded = respond_to_audit_observation(
        observation_id=obs.id,
        user_id=1002,
        acting_role="basic_user",
        response_text="Asset tag was ordered",
    )
    assert responded.status == AuditObservationStatus.RESPONDED

    reopened = review_and_close_observation(
        observation_id=obs.id,
        auditor_id=6001,
        acting_role="audit_officer",
        is_satisfactory=False,
        remarks="Proof of tagging required before closing",
    )
    assert reopened.status == AuditObservationStatus.OPEN

    respond_to_audit_observation(
        observation_id=obs.id,
        user_id=1002,
        acting_role="basic_user",
        response_text="Attached photo of spectrometer with tag #ME-882",
    )

    closed = review_and_close_observation(
        observation_id=obs.id,
        auditor_id=6001,
        acting_role="audit_officer",
        is_satisfactory=True,
        remarks="Asset tag verified on photo. Closed.",
    )
    assert closed.status == AuditObservationStatus.CLOSED
    assert closed.closed_at is not None
