"""Who sees which rows, decided once; anything outside answers 404 (BR-PMS-003, 006, 130)."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.pms.domain import documents as d
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Appeal,
    Application,
    AttorneyAssignment,
    AuditEntry,
    Budget,
    DirectorProfile,
    Document,
    DocumentVersion,
    Escalation,
    Inventor,
    LicensingRequest,
    MaintenanceCycle,
    OfficeAction,
    PriorArtReference,
    ReviewCycle,
)

# The permission that marks each role's lane; scope never widens beyond the acting role.
P_ADMIN = "pms.review.assign"
P_DIRECTOR = "pms.review.approve"
P_ATTORNEY = "pms.attorney_assignment.review"
P_APPLICANT = "pms.application.create"

ADMIN, DIRECTOR, ATTORNEY, APPLICANT, NOBODY = ("pcc_admin", "director", "attorney",
                                                "applicant", "nobody")


def lane(actor) -> str:
    has = getattr(actor, "has_permission", None)
    if has is None or getattr(actor, "user_id", None) is None:
        return NOBODY
    if has(P_ADMIN):
        return ADMIN
    if has(P_DIRECTOR):
        return DIRECTOR
    if has(P_ATTORNEY):
        return ATTORNEY
    if has(P_APPLICANT):
        return APPLICANT
    return NOBODY


def director_domains(user_id: int) -> list[str]:
    profile = DirectorProfile.objects.filter(user_id=user_id, valid_to__isnull=True).first()
    return list(profile.domain_codes) if profile else []


def _director_q(user_id: int) -> Q:
    """Applications a Director acts on, plus their areas for oversight (ruling C13)."""
    return (Q(pk__in=ReviewCycle.objects.filter(director_user_id=user_id)
              .values("application_id"))
            | Q(pk__in=Appeal.objects.filter(director_user_id=user_id)
                .values("application_id"))
            | Q(pk__in=MaintenanceCycle.objects.filter(deciding_director_user_id=user_id)
                .values("application_id"))
            | Q(domain_code__in=director_domains(user_id)))


def _attorney_q(user_id: int) -> Q:
    return Q(pk__in=AttorneyAssignment.objects.filter(
        attorney_user_id=user_id, status__in=sorted(sm.LIVE_ASSIGNMENT))
        .values("application_id"))


def _applicant_q(user_id: int) -> Q:
    """Own applications, plus non-draft ones naming them as an inventor (blueprint Q-10)."""
    as_inventor = Inventor.objects.filter(user_id=user_id).values("application_id")
    return Q(applicant_user_id=user_id) | (Q(pk__in=as_inventor) & ~Q(status=sm.DRAFT))


def applications_for(actor) -> QuerySet[Application]:
    base = Application.objects.all()
    who, uid = lane(actor), getattr(actor, "user_id", None)
    if who == ADMIN:
        return base.exclude(status=sm.DRAFT)
    if who == DIRECTOR:
        return base.filter(_director_q(uid)).exclude(status=sm.DRAFT)
    if who == ATTORNEY:
        return base.filter(_attorney_q(uid))
    if who == APPLICANT:
        return base.filter(_applicant_q(uid))
    return base.none()


def relations(actor, application: Application) -> frozenset[str]:
    """How this person stands to one application, for document access (BR-PMS-084, 086)."""
    uid, who = actor.user_id, lane(actor)
    rel: set[str] = set()
    if who == ADMIN:
        rel.add(d.PCC_ADMIN)
    if who == APPLICANT:
        if application.applicant_user_id == uid:
            rel.add(d.APPLICANT)
        if application.inventors.filter(user_id=uid).exists():
            rel.add(d.INVENTOR)
    if who == ATTORNEY and application.attorney_assignments.filter(
            attorney_user_id=uid, status__in=sorted(sm.LIVE_ASSIGNMENT)).exists():
        rel.add(d.ATTORNEY)
    if who == DIRECTOR:
        if reviewing_director_id(application) == uid \
                or application.appeals.filter(director_user_id=uid, status="open").exists() \
                or application.maintenance_cycles.filter(
                    deciding_director_user_id=uid, status__in=sorted(sm.LIVE_CYCLE)).exists():
            rel.add(d.REVIEWING_DIRECTOR)
        elif application.review_cycles.filter(director_user_id=uid).exists():
            rel.add(d.PAST_DIRECTOR)
        if application.domain_code in director_domains(uid):
            rel.add(d.AREA_DIRECTOR)
    return frozenset(rel)


def reviewing_director_id(application: Application) -> int | None:
    """The Director of the latest review cycle: they decide the budget and renewals too."""
    latest = application.review_cycles.order_by("-cycle_no").first()
    return latest.director_user_id if latest else None


def documents_for(actor, application: Application) -> list[tuple[Document, list]]:
    """Documents on an application the actor can see, each with only its readable versions."""
    rel = relations(actor, application)
    return [(doc, sorted(doc.versions.all(), key=lambda v: -v.number))
            for doc in (Document.objects.filter(application=application)
                        .prefetch_related("versions").order_by("id"))
            if d.may_read(rel, doc.sensitivity)]


def version_for(actor, version_id: int) -> DocumentVersion | None:
    version = (DocumentVersion.objects.select_related("document", "document__application")
               .filter(pk=version_id,
                       document__application__in=applications_for(actor)).first())
    if version is None:
        return None
    rel = relations(actor, version.document.application)
    return version if d.may_read(rel, version.document.sensitivity) else None


def prior_art_for(actor) -> QuerySet[PriorArtReference]:
    return PriorArtReference.objects.filter(application__in=applications_for(actor))


def budgets_for(actor) -> QuerySet[Budget]:
    return Budget.objects.select_related("application").filter(
        application__in=applications_for(actor))


def office_actions_for(actor) -> QuerySet[OfficeAction]:
    return (OfficeAction.objects.select_related("application", "communication")
            .prefetch_related("extensions")
            .filter(application__in=applications_for(actor)))


def maintenance_for(actor) -> QuerySet[MaintenanceCycle]:
    return MaintenanceCycle.objects.select_related("application").filter(
        application__in=applications_for(actor))


def appeals_for(actor) -> QuerySet[Appeal]:
    return Appeal.objects.select_related("application").filter(
        application__in=applications_for(actor))


def assignments_for(actor) -> QuerySet[AttorneyAssignment]:
    qs = AttorneyAssignment.objects.select_related("application")
    who = lane(actor)
    if who == ATTORNEY:
        return qs.filter(attorney_user_id=actor.user_id)
    return qs.filter(application__in=applications_for(actor))


def licensing_for(actor) -> QuerySet[LicensingRequest]:
    """BR-PMS-091 / ruling C20: the applicant, the routed Director and PCC_ADMIN only."""
    base = LicensingRequest.objects.select_related("application")
    who, uid = lane(actor), getattr(actor, "user_id", None)
    if who == ADMIN:
        return base
    if who == DIRECTOR:
        return base.filter(routed_director_user_id=uid)
    if who == APPLICANT:
        return base.filter(applicant_user_id=uid)
    return base.none()


def escalations_for(actor) -> QuerySet[Escalation]:
    if lane(actor) != ADMIN:
        return Escalation.objects.none()
    return Escalation.objects.select_related("application")


def audit_for(actor) -> QuerySet[AuditEntry]:
    """UC-PMS-028 / ruling C21: PCC_ADMIN everything; a Director their own applications."""
    who = lane(actor)
    base = AuditEntry.objects.select_related("application")
    if who == ADMIN:
        return base
    if who == DIRECTOR:
        return base.filter(application__in=applications_for(actor))
    return base.none()

