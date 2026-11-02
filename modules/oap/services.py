from django.db import transaction
from django.utils import timezone
from core.api.exceptions import ConflictError, PermissionDeniedError
from .models import AssistantshipClaim, NoDuesClearance, NoDuesRequest

DOMAIN_PERMISSIONS = {"library":"oap.no_dues.verify_library", "hostel":"oap.no_dues.verify_hostel", "mess":"oap.no_dues.verify_mess", "department":"oap.no_dues.verify_department", "lab":"oap.no_dues.verify_lab", "academic_section":"oap.no_dues.verify_academic_section", "student_section":"oap.no_dues.verify_student_section"}

def _must(actor, permission):
    if not actor.has_permission(permission): raise PermissionDeniedError()

@transaction.atomic
def start_no_dues(*, student_user_id):
    request = NoDuesRequest.objects.create(student_user_id=student_user_id)
    NoDuesClearance.objects.bulk_create([NoDuesClearance(request=request, domain=d) for d in NoDuesClearance.DOMAINS])
    return request

@transaction.atomic
def verify_no_dues(*, clearance, actor, status):
    if status not in {"cleared", "dues_outstanding"}: raise ConflictError("invalid_clearance_status")
    _must(actor, DOMAIN_PERMISSIONS[clearance.domain])
    if clearance.request.status == "finalized" or clearance.status != "pending": raise ConflictError("clearance_not_pending")
    clearance.status, clearance.verified_by_user_id, clearance.verified_at = status, actor.user_id, timezone.now(); clearance.save()
    return clearance

@transaction.atomic
def finalize_no_dues(*, request, actor, certificate_url=""):
    _must(actor, "oap.no_dues.finalize")
    if request.status != "in_progress" or request.clearances.count() != 7 or request.clearances.exclude(status="cleared").exists(): raise ConflictError("clearances_not_complete")
    request.status, request.finalized_by_user_id, request.finalized_at, request.certificate_url = "finalized", actor.user_id, timezone.now(), certificate_url; request.save(); return request

@transaction.atomic
def verify_claim(*, claim, actor, role, approved):
    if role not in {"thesis", "ta"} or actor.user_id != getattr(claim, f"{role}_supervisor_user_id"): raise PermissionDeniedError()
    if claim.status != "submitted": raise ConflictError("claim_not_awaiting_supervisors")
    setattr(claim, f"{role}_decision", "approved" if approved else "rejected"); setattr(claim, f"{role}_decided_at", timezone.now())
    if not approved: claim.status = "rejected"
    elif claim.thesis_decision == "approved" and claim.ta_decision == "approved": claim.status = "awaiting_department"
    claim.save(); return claim

@transaction.atomic
def forward_claim(*, claim, actor):
    _must(actor, "oap.assistantship.review")
    if claim.status != "awaiting_department": raise ConflictError("supervisor_gate_not_met")
    claim.status, claim.department_reviewed_by_user_id = "forwarded_to_hod", actor.user_id; claim.save(); return claim
