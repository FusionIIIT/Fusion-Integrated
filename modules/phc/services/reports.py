from modules.directory.contracts import get_users
from modules.phc.models import PatientVisit
from modules.phc.selectors import reports as report_selectors


def aggregate_report(report_type: str) -> dict:
    if report_type == "visits":
        return {"total": PatientVisit.objects.count(),
                "by_month": list(report_selectors.service_utilization_by_month())}
    if report_type == "inventory":
        return {"consumption": list(report_selectors.inventory_consumption())}
    if report_type == "ambulance":
        return {"by_month": list(report_selectors.ambulance_usage_by_month())}
    if report_type == "reimbursements":
        return {"by_state": list(report_selectors.reimbursement_status_counts())}
    if report_type == "demographics":
        patient_ids = list(PatientVisit.objects.values_list(
            "patient_user_id", flat=True).distinct())
        counts = {}
        for offset in range(0, len(patient_ids), 500):
            users = get_users(patient_ids[offset:offset + 500])
            for user in users.values():
                counts[user.kind] = counts.get(user.kind, 0) + 1
        return {"total": len(patient_ids), "by_kind": counts}
    raise ValueError("Choose visits, inventory, ambulance, reimbursements, or demographics.")
