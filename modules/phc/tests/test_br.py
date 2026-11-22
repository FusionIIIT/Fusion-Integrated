"""BR strategy: boundary, authorization, privacy and audit rules."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


def test_claim_submit_requires_employee_own_prescription_expense_date(phc_client, prescription):
    student = phc_client(uid=1001, kind="student", permissions=("phc.claim.submit",))
    payload = {"prescription_id": prescription.pk, "amount_claimed": "20.00"}
    assert student.post("/api/v1/phc/claims/submit/", payload, format="json").status_code == 403
    employee = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.submit",))
    assert employee.post("/api/v1/phc/claims/submit/", payload, format="json").status_code == 201
    other = phc_client(uid=2002, kind="staff", permissions=("phc.claim.submit",))
    assert other.post("/api/v1/phc/claims/submit/", payload, format="json").status_code == 409


def test_claimant_only_sees_own_claims_and_status_change_notifies(prescription, phc_client):
    from modules.phc.models import PhcNotification, ReimbursementClaim

    claim = ReimbursementClaim.objects.create(
        user_id=1001, prescription=prescription, amount_claimed=Decimal("12.00")
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.claim.review_phc",))
    assert staff.post(f"/api/v1/phc/claims/{claim.pk}/review/").status_code == 200
    assert PhcNotification.objects.filter(
        recipient_user_id=1001, event_type="claim_status_changed"
    ).exists()
    claimant = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.view_self",))
    assert claimant.get(f"/api/v1/phc/claims/my/{claim.pk}/").status_code == 200
    foreign = phc_client(uid=2002, kind="faculty", permissions=("phc.claim.view_self",))
    assert foreign.get(f"/api/v1/phc/claims/my/{claim.pk}/").status_code == 404


def test_submission_window_configuration_is_staff_only(phc_client):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.claim.configure",))
    changed = staff.patch(
        "/api/v1/phc/claims/config/", {"submission_window_days": 30}, format="json"
    )
    assert changed.status_code == 200
    assert changed.json()["submission_window_days"] == 30
    patient = phc_client(uid=1001, permissions=())
    assert patient.get("/api/v1/phc/claims/config/").status_code == 403


def test_inventory_adjustment_audits_and_alerts_below_threshold(phc_client):
    from modules.phc.models import InventoryAudit, InventoryItem, PhcNotification

    item = InventoryItem.objects.create(
        name="Bandage", stock_quantity=Decimal("6"), reorder_threshold=Decimal("5")
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.inventory.manage",))
    response = staff.post(
        f"/api/v1/phc/inventory/{item.pk}/adjust/", {"delta": "-2"}, format="json"
    )
    assert response.status_code == 200
    assert InventoryAudit.objects.filter(item=item, quantity_after=Decimal("4")).exists()
    assert PhcNotification.objects.filter(
        recipient_user_id=900, event_type="low_stock_alert"
    ).exists()
    assert (
        staff.post(
            f"/api/v1/phc/inventory/{item.pk}/adjust/", {"delta": "-99"}, format="json"
        ).status_code
        == 409
    )


def test_reports_do_not_expose_patient_identifiers(phc_client, visit):
    staff = phc_client(uid=900, kind="staff", permissions=("phc.report.view",))
    response = staff.get("/api/v1/phc/reports/?type=demographics")
    assert response.status_code == 200
    assert "user_id" not in response.content.decode()
    assert "chief_complaint" not in response.content.decode()


def test_demographics_report_aggregates_visits_by_patient_category(phc_client, monkeypatch):
    from types import SimpleNamespace

    from modules.directory import contracts as directory_contracts
    from modules.phc.models import PatientVisit

    PatientVisit.objects.create(
        user_id=1001,
        visit_date="2026-11-01",
        chief_complaint="A",
        recorded_by_user_id=900,
    )
    PatientVisit.objects.create(
        user_id=1001,
        visit_date="2026-11-02",
        chief_complaint="B",
        recorded_by_user_id=900,
    )
    PatientVisit.objects.create(
        user_id=2002,
        visit_date="2026-11-02",
        chief_complaint="C",
        recorded_by_user_id=900,
    )
    monkeypatch.setattr(
        directory_contracts,
        "get_users",
        lambda user_ids: {
            1001: SimpleNamespace(kind="student"),
            2002: SimpleNamespace(kind="faculty"),
        },
    )
    staff = phc_client(uid=900, kind="staff", permissions=("phc.report.view",))
    response = staff.get("/api/v1/phc/reports/?type=demographics")
    assert response.status_code == 200
    assert response.json()["patient_groups"] == [
        {"category": "employee", "patients": 1, "visits": 1},
        {"category": "student", "patients": 1, "visits": 2},
    ]


@pytest.mark.parametrize(
    "amount", ["0", "-0.01", "invalid"], ids=["zero-amount", "negative-amount", "non-numeric-amount"]
)
def test_br_claim_amount_must_be_a_positive_decimal(phc_client, prescription, amount):
    client = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.submit",))
    response = client.post(
        "/api/v1/phc/claims/submit/",
        {"prescription_id": prescription.pk, "amount_claimed": amount},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "scenario", ["missing-amount", "extra-decimal-place", "unknown-prescription", "missing-expense-date"],
    ids=["amount-required", "money-precision-limited", "prescription-must-exist", "expense-date-required"],
)
def test_br_claim_requires_complete_money_and_prescription_evidence(
    phc_client, prescription, visit, scenario
):
    from modules.phc.models import Prescription

    payload = {"prescription_id": prescription.pk, "amount_claimed": "1.00"}
    expected = 400
    if scenario == "missing-amount":
        payload.pop("amount_claimed")
    elif scenario == "extra-decimal-place":
        payload["amount_claimed"] = "1.001"
    elif scenario == "unknown-prescription":
        payload["prescription_id"] = 999999
        expected = 409
    else:
        missing_date_rx = Prescription.objects.create(
            user_id=visit.user_id,
            visit=visit,
            medicine_name="No date", dosage="once", prescribed_by_user_id=900,
        )
        payload["prescription_id"] = missing_date_rx.pk
        expected = 409
    response = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.submit",)).post(
        "/api/v1/phc/claims/submit/", payload, format="json"
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    "submission_day,expected",
    [("2026-10-01", 201), ("2026-11-30", 201), ("2026-12-01", 409), ("2026-09-30", 409)],
    ids=["expense-day", "last-allowed-day", "first-expired-day", "expense-after-submission"],
)
def test_br_claim_submission_window_includes_limit_and_rejects_outside(
    phc_client, prescription, monkeypatch, submission_day, expected
):
    import datetime as dt

    from modules.phc.models import ReimbursementConfig
    from modules.phc.services import reimbursement

    ReimbursementConfig.objects.create(submission_window_days=60)
    monkeypatch.setattr(reimbursement.timezone, "localdate", lambda: dt.date.fromisoformat(submission_day))
    response = phc_client(uid=1001, kind="faculty", permissions=("phc.claim.submit",)).post(
        "/api/v1/phc/claims/submit/",
        {"prescription_id": prescription.pk, "amount_claimed": "10.00"},
        format="json",
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    "path,method",
    [
        ("/api/v1/phc/schedules/create/", "post"),
        ("/api/v1/phc/schedules/1/publish/", "post"),
        ("/api/v1/phc/attendance/mark/", "post"),
        ("/api/v1/phc/visits/", "get"),
        ("/api/v1/phc/patients/search/?q=Me", "get"),
        ("/api/v1/phc/visits/create/", "post"),
        ("/api/v1/phc/claims/submit/", "post"),
        ("/api/v1/phc/claims/1/review/", "post"),
        ("/api/v1/phc/claims/1/verify/", "post"),
        ("/api/v1/phc/claims/1/decide/", "post"),
        ("/api/v1/phc/inventory/", "get"),
        ("/api/v1/phc/requisitions/create/", "post"),
    ],
    ids=["schedule-create", "schedule-publish", "attendance-mark", "staff-visits", "patient-search", "visit-create", "claim-submit", "claim-phc-review", "claim-accounts-verify", "claim-authority-decision", "inventory-view", "requisition-submit"],
)
def test_br_module_member_without_function_permission_is_denied(phc_client, path, method):
    client = phc_client(uid=777, kind="student", permissions=(), modules=("phc",))
    response = getattr(client, method)(path, {}, format="json") if method == "post" else client.get(path)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "payload", [{"delta": "0"}, {"delta": "not-a-number"}, {"delta": "0.001"}],
    ids=["zero-change", "malformed-change", "excess-precision"],
)
def test_br_inventory_adjustment_rejects_zero_or_malformed_delta(phc_client, payload):
    from modules.phc.models import InventoryItem

    item = InventoryItem.objects.create(name="BR item", stock_quantity=Decimal("5"))
    response = phc_client(uid=900, kind="staff", permissions=("phc.inventory.manage",)).post(
        f"/api/v1/phc/inventory/{item.pk}/adjust/", payload, format="json"
    )
    assert response.status_code == 400
    item.refresh_from_db()
    assert item.stock_quantity == Decimal("5")


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "Empty", "line_items": []},
        {"title": "No lines"},
        {"title": "No item name", "line_items": [{"quantity": "1"}]},
        {"title": "No quantity", "line_items": [{"item_name": "Mask"}]},
    ],
    ids=["empty-lines", "missing-lines", "missing-item-name", "missing-quantity"],
)
def test_br_requisition_requires_at_least_one_well_formed_line(phc_client, payload):
    response = phc_client(uid=900, kind="staff", permissions=("phc.requisition.submit",)).post(
        "/api/v1/phc/requisitions/create/", payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("field", ["patient_name", "destination"], ids=["patient-name", "destination"])
def test_br_ambulance_log_requires_non_blank_required_text(phc_client, field):
    payload = {"patient_name": "Patient", "destination": "Hospital", "usage_at": "2026-11-20T10:30:00Z"}
    payload[field] = "   "
    response = phc_client(uid=900, kind="staff", permissions=("phc.ambulance.log",)).post(
        "/api/v1/phc/ambulance/log/", payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("field", ["title", "body"], ids=["announcement-title", "announcement-body"])
def test_br_announcement_requires_non_blank_title_and_body(phc_client, field):
    payload = {"title": "Health update", "body": "Clinic information"}
    payload[field] = "   "
    response = phc_client(uid=900, kind="staff", permissions=("phc.announcement.publish",)).post(
        "/api/v1/phc/announcements/publish/", payload, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("recipient", [1001, -1], ids=["single-user", "broadcast"])
def test_br_notification_outbox_marks_queued_messages_delivered(recipient):
    from modules.phc.models import PhcNotification
    from modules.phc.services.notifications import deliver_pending

    notification = PhcNotification.objects.create(
        recipient_user_id=recipient,
        event_type="claim_status_changed",
        subject="PHC status",
        body="Claim updated",
    )
    result = deliver_pending()
    notification.refresh_from_db()
    assert result == {"delivered": 1, "failed": 0, "skipped": 0}
    assert notification.delivered is True
    assert notification.delivered_at is not None
    assert notification.attempts == (0 if recipient == -1 else 1)


@pytest.mark.django_db
def test_br_notification_outbox_respects_delivery_batch_limit():
    from modules.phc.models import PhcNotification
    from modules.phc.services.notifications import deliver_pending

    notifications = [
        PhcNotification.objects.create(
            recipient_user_id=user_id,
            event_type="claim_status_changed",
            subject=f"Status {user_id}",
            body="Updated",
        )
        for user_id in (101, 102, 103)
    ]
    result = deliver_pending(limit=2)
    assert result == {"delivered": 2, "failed": 0, "skipped": 0}
    delivered_ids = set(
        PhcNotification.objects.filter(delivered=True).values_list("id", flat=True)
    )
    assert delivered_ids == {notifications[0].pk, notifications[1].pk}


@pytest.mark.django_db
def test_br_notification_delivery_failure_is_counted_and_attempt_is_saved(monkeypatch):
    from modules.phc.models import PhcNotification
    from modules.phc.services.notifications import deliver_pending

    notification = PhcNotification.objects.create(
        recipient_user_id=101,
        event_type="claim_status_changed",
        subject="Will retry",
        body="Delivery transient error",
    )
    original_save = PhcNotification.save
    failed_once = False

    def fail_delivery_save(self, *args, **kwargs):
        nonlocal failed_once
        if self.pk == notification.pk and not failed_once and "delivered" in kwargs.get("update_fields", ()):
            failed_once = True
            raise RuntimeError("temporary delivery failure")
        return original_save(self, *args, **kwargs)

    monkeypatch.setattr(PhcNotification, "save", fail_delivery_save)
    result = deliver_pending()
    notification.refresh_from_db()
    assert result == {"delivered": 0, "failed": 1, "skipped": 0}
    assert notification.delivered is False
    assert notification.attempts == 1


@pytest.mark.parametrize(
    "operation,field",
    [("ambulance", "patient_name"), ("ambulance", "destination"), ("announcement", "title"), ("announcement", "body")],
    ids=["blank-ambulance-patient", "blank-ambulance-destination", "blank-advisory-title", "blank-advisory-body"],
)
def test_br_services_reject_blank_required_text(operation, field):
    from datetime import datetime

    from core.api.exceptions import BadRequestError
    from modules.phc.services.operations import log_ambulance_usage, publish_announcement

    if operation == "ambulance":
        values = {"patient_name": "Patient", "destination": "Hospital"}
        values[field] = "   "
        with pytest.raises(BadRequestError):
            log_ambulance_usage(
                **values, usage_at=datetime(2026, 11, 20, 10, 0), actor_user_id=900
            )
    else:
        values = {"title": "Alert", "body": "Details"}
        values[field] = "   "
        with pytest.raises(BadRequestError):
            publish_announcement(**values, actor_user_id=900)


@pytest.mark.parametrize("directory_result", [None, "unknown-kind"], ids=["missing-directory-user", "unrecognized-directory-kind"])
def test_br_demographics_report_groups_unmatched_profiles_as_unclassified(
    monkeypatch, directory_result
):
    from types import SimpleNamespace

    from modules.directory import contracts as directory_contracts
    from modules.phc.models import PatientVisit
    from modules.phc.services.operations import generate_report

    PatientVisit.objects.create(
        user_id=77, visit_date="2026-11-03", chief_complaint="A", recorded_by_user_id=900
    )
    user = None if directory_result is None else SimpleNamespace(kind="visitor")
    monkeypatch.setattr(directory_contracts, "get_users", lambda user_ids: {77: user} if user else {})
    report = generate_report("demographics")
    assert report["patient_groups"] == [{"category": "unclassified", "patients": 1, "visits": 1}]


@pytest.mark.django_db
def test_br_demographics_report_is_empty_when_no_patient_visits(monkeypatch):
    from modules.directory import contracts as directory_contracts
    from modules.phc.services.operations import generate_report

    monkeypatch.setattr(directory_contracts, "get_users", lambda user_ids: {})
    report = generate_report("demographics")
    assert report["total_visits"] == 0
    assert report["patient_groups"] == []


@pytest.mark.django_db
def test_br_utilization_report_groups_visits_by_calendar_month():
    from modules.phc.models import PatientVisit
    from modules.phc.services.operations import generate_report

    for day in ("2026-10-01", "2026-10-31", "2026-11-01"):
        PatientVisit.objects.create(
            user_id=1001, visit_date=day, chief_complaint="Monthly", recorded_by_user_id=900
        )
    report = generate_report("utilization")
    assert report["rows"] == [
        {"month": "2026-10-01", "visits": 2},
        {"month": "2026-11-01", "visits": 1},
    ]


@pytest.mark.django_db
def test_br_unknown_report_type_is_rejected(phc_client):
    client = phc_client(uid=900, kind="staff", permissions=("phc.report.view",))
    response = client.get("/api/v1/phc/reports/?type=patient-list")
    assert response.status_code == 400


@pytest.mark.django_db
def test_br_inventory_report_marks_only_below_threshold_items_as_low_stock(phc_client):
    from modules.phc.models import InventoryItem

    InventoryItem.objects.create(
        name="Below", stock_quantity=Decimal("1"), reorder_threshold=Decimal("2")
    )
    InventoryItem.objects.create(
        name="At", stock_quantity=Decimal("2"), reorder_threshold=Decimal("2")
    )
    response = phc_client(uid=900, kind="staff", permissions=("phc.report.view",)).get(
        "/api/v1/phc/reports/?type=inventory"
    )
    assert response.status_code == 200
    assert {
        row["name"]: row["is_low_stock"] for row in response.json()["items"]
    } == {"Below": True, "At": False}
