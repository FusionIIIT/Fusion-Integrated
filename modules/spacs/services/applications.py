from collections.abc import Mapping
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.domain.policies import (
    ApplicationField,
    EligibilityRule,
    EvidenceRequirement,
    validate_required_evidence,
    validate_required_fields,
)
from modules.spacs.domain.state_machine import (
    SCHOLARSHIP_APPLICATION,
    ActorNotAllowed,
    AmbiguousTransition,
    InvalidTransition,
    Transition,
    resolve,
)
from modules.spacs.models import (
    Application,
    ApplicationEvidence,
    ApplicationTransition,
    AuditEvent,
    CatalogueEntry,
    CatalogueVersion,
    NotificationOutbox,
    WorkflowTask,
)
from modules.spacs.services.catalogue import application_window_open
from modules.spacs.services.contracts import (
    DocumentStorage,
    EligibilityEvaluator,
    EligibilityResult,
    configured_document_storage,
    configured_eligibility_evaluator,
)
from modules.spacs.services.errors import IntegrationUnavailableError

_TERMINAL_APPLICATION_STATES = {"Approved", "Rejected", "Withdrawn"}


def _policy_items(
    configuration: object,
    key: str,
) -> list[Mapping[str, object]]:
    if not isinstance(configuration, dict):
        raise BadRequestError(
            "Catalogue configuration must be a JSON object.",
            code="invalid_configuration",
        )
    values = configuration.get(key, [])
    if not isinstance(values, list) or any(not isinstance(value, dict) for value in values):
        raise BadRequestError(
            f"{key} must be an array of objects.",
            code="invalid_policy_configuration",
        )
    return values


def _required_text(item: Mapping[str, object], key: str, section: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BadRequestError(
            f"{section} entries require a non-empty {key}.",
            code="invalid_policy_configuration",
        )
    return value


def _optional_mapping(
    item: Mapping[str, object],
    key: str,
    section: str,
) -> Mapping[str, object] | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise BadRequestError(
            f"{section} {key} must be an object.",
            code="invalid_policy_configuration",
        )
    return value


def _application_fields(configuration: object) -> list[ApplicationField]:
    items = _policy_items(configuration, "application_fields")
    fields = []
    for item in items:
        required = item.get("required")
        if not isinstance(required, bool):
            raise BadRequestError(
                "Application field required values must be boolean.",
                code="invalid_policy_configuration",
            )
        fields.append(
            ApplicationField(
                field_id=_required_text(item, "field_id", "Application field"),
                name=_required_text(item, "name", "Application field"),
                data_type=_required_text(item, "data_type", "Application field"),
                required=required,
                validation=_optional_mapping(item, "validation", "Application field"),
                display_metadata=_optional_mapping(item, "display_metadata", "Application field"),
            )
        )
    field_ids = [field.field_id for field in fields]
    if len(field_ids) != len(set(field_ids)):
        raise BadRequestError(
            "Application field identifiers must be unique.",
            code="invalid_policy_configuration",
        )
    return fields


def _eligibility_rules(configuration: object) -> list[EligibilityRule]:
    items = _policy_items(configuration, "eligibility_rules")
    rules = []
    for item in items:
        data_sources = item.get("data_sources", [])
        if not isinstance(data_sources, list) or any(
            not isinstance(source, str) for source in data_sources
        ):
            raise BadRequestError(
                "Eligibility rule data_sources must be an array of strings.",
                code="invalid_policy_configuration",
            )
        rules.append(
            EligibilityRule(
                rule_id=_required_text(item, "rule_id", "Eligibility rule"),
                condition=item.get("condition"),
                data_sources=tuple(data_sources),
            )
        )
    rule_ids = [rule.rule_id for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise BadRequestError(
            "Eligibility rule identifiers must be unique.",
            code="invalid_policy_configuration",
        )
    return rules


def configured_evidence_requirements(
    configuration: object,
) -> list[EvidenceRequirement]:
    items = _policy_items(configuration, "evidence_requirements")
    requirements = []
    for item in items:
        required = item.get("required")
        if not isinstance(required, bool):
            raise BadRequestError(
                "Evidence requirement values must be boolean.",
                code="invalid_policy_configuration",
            )
        requirements.append(
            EvidenceRequirement(
                requirement_id=_required_text(item, "requirement_id", "Evidence requirement"),
                evidence_type=_required_text(item, "evidence_type", "Evidence requirement"),
                required=required,
                applicable_condition=item.get("applicable_condition"),
                submission=_optional_mapping(item, "submission", "Evidence requirement"),
                verification=_optional_mapping(item, "verification", "Evidence requirement"),
            )
        )
    requirement_ids = [item.requirement_id for item in requirements]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise BadRequestError(
            "Evidence requirement identifiers must be unique.",
            code="invalid_policy_configuration",
        )
    return requirements


def _audit_application(
    *,
    application: Application,
    actor_user_id: int,
    event_type: str,
    payload: dict[str, object],
) -> None:
    AuditEvent.objects.create(
        aggregate_type="application",
        aggregate_id=str(application.public_id),
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_label="Student",
        payload=payload,
    )


@transaction.atomic
def start_application(
    *,
    user_id: int,
    catalogue_version_id: int,
    academic_cycle: str,
) -> Application:
    version_reference = (
        CatalogueVersion.objects.filter(pk=catalogue_version_id).values("entry_id").first()
    )
    if version_reference is None:
        raise NotFoundError("No such catalogue version.")

    entry = (
        CatalogueEntry.objects.select_for_update().filter(pk=version_reference["entry_id"]).first()
    )
    if entry is None:
        raise NotFoundError("No such catalogue version.")
    version = (
        CatalogueVersion.objects.select_for_update()
        .select_related("entry")
        .filter(pk=catalogue_version_id, entry=entry)
        .first()
    )
    if version is None:
        raise NotFoundError("No such catalogue version.")
    if entry.kind != "scholarship":
        raise ConflictError(
            "Applications can only be started for scholarship catalogue entries.",
            code="not_a_scholarship",
        )
    if not application_window_open(version):
        raise ConflictError(
            "The scholarship application window is not open.",
            code="application_window_closed",
        )
    if not isinstance(version.configuration, dict):
        raise BadRequestError(
            "Catalogue configuration must be a JSON object.",
            code="invalid_configuration",
        )
    if not isinstance(academic_cycle, str) or not academic_cycle.strip():
        raise BadRequestError(
            "An academic cycle is required.",
            code="invalid_academic_cycle",
        )

    duplicate_permitted = version.configuration.get("duplicate_applications_permitted") is True
    if (
        not duplicate_permitted
        and Application.objects.filter(
            user_id=user_id,
            catalogue_version__entry=entry,
            academic_cycle=academic_cycle,
            kind="scholarship",
        )
        .exclude(state__in=_TERMINAL_APPLICATION_STATES)
        .exists()
    ):
        raise ConflictError(
            "An active application already exists for this scholarship and cycle.",
            code="duplicate_application",
        )

    application = Application.objects.create(
        user_id=user_id,
        catalogue_version=version,
        kind="scholarship",
        academic_cycle=academic_cycle,
        state="Not Started / Draft",
    )
    _audit_application(
        application=application,
        actor_user_id=user_id,
        event_type="application.draft_started",
        payload={
            "catalogue_version_id": version.pk,
            "academic_cycle": academic_cycle,
        },
    )
    return application


def _owned_application(*, application_id: UUID, user_id: int) -> Application:
    application = (
        Application.objects.select_for_update()
        .select_related("catalogue_version", "catalogue_version__entry")
        .filter(public_id=application_id, user_id=user_id)
        .first()
    )
    if application is None:
        raise NotFoundError("No such application.")
    return application


@transaction.atomic
def save_draft(
    *,
    application_id: UUID,
    user_id: int,
    application_data: Mapping[str, object],
) -> Application:
    if not isinstance(application_data, Mapping):
        raise BadRequestError(
            "Application data must be an object.",
            code="invalid_application_data",
        )
    application = _owned_application(
        application_id=application_id,
        user_id=user_id,
    )
    if application.state not in {"Not Started / Draft", "Correction Required"}:
        raise ConflictError(
            "The application is not in a state that permits draft changes.",
            code="application_not_editable",
        )

    application.application_data = dict(application_data)
    application.save(update_fields=["application_data", "updated_at"])
    _audit_application(
        application=application,
        actor_user_id=user_id,
        event_type="application.draft_saved",
        payload={"field_ids": sorted(application.application_data)},
    )
    return application


def _validate_submission(
    *,
    application: Application,
    eligibility_evaluator: EligibilityEvaluator | None,
    document_storage: DocumentStorage | None,
    evaluate_eligibility: bool,
) -> None:
    configuration = application.catalogue_version.configuration
    fields = _application_fields(configuration)
    if any(field.validation for field in fields):
        raise IntegrationUnavailableError(
            "Configured application-field validation is not available."
        )
    missing_fields = validate_required_fields(fields, application.application_data)
    if missing_fields:
        raise ConflictError(
            "Required application fields are missing.",
            code="required_fields_missing",
            details=[{"field_id": field_id} for field_id in missing_fields],
        )

    if evaluate_eligibility:
        rules = _eligibility_rules(configuration)
        if rules:
            if eligibility_evaluator is None:
                eligibility_evaluator = configured_eligibility_evaluator()
            result = eligibility_evaluator.evaluate(
                user_id=application.user_id,
                application=application,
                version=application.catalogue_version,
            )
            if not isinstance(result, EligibilityResult):
                raise IntegrationUnavailableError(
                    "The eligibility evaluator returned an unsupported result."
                )
            if not result.satisfied:
                raise ConflictError(
                    "The application does not satisfy mandatory eligibility criteria.",
                    code="eligibility_not_satisfied",
                    details=[
                        {"criterion_id": criterion_id}
                        for criterion_id in result.failed_criterion_ids
                    ],
                )

    evidence_requirements = configured_evidence_requirements(configuration)
    conditional_required = [
        requirement.requirement_id
        for requirement in evidence_requirements
        if requirement.required and requirement.applicable_condition is not None
    ]
    if conditional_required:
        raise IntegrationUnavailableError(
            "Conditional evidence applicability cannot be evaluated.",
        )
    if any(
        requirement.required and requirement.verification for requirement in evidence_requirements
    ):
        raise IntegrationUnavailableError(
            "Configured evidence verification is not available.",
        )
    required_requirements = [
        requirement for requirement in evidence_requirements if requirement.required
    ]
    supplied_ids = set(
        ApplicationEvidence.objects.filter(application=application).values_list(
            "requirement_id", flat=True
        )
    )
    missing_evidence = validate_required_evidence(
        required_requirements,
        supplied_ids,
    )
    if missing_evidence:
        raise ConflictError(
            "Required evidence is missing.",
            code="required_evidence_missing",
            details=[{"requirement_id": requirement_id} for requirement_id in missing_evidence],
        )

    evidence_by_requirement: dict[str, list[ApplicationEvidence]] = {}
    for evidence in ApplicationEvidence.objects.filter(
        application=application,
        requirement_id__in=[item.requirement_id for item in required_requirements],
    ):
        evidence_by_requirement.setdefault(evidence.requirement_id, []).append(evidence)
    for requirement in required_requirements:
        evidence_records = evidence_by_requirement.get(requirement.requirement_id, [])
        if document_storage is None and evidence_records:
            document_storage = configured_document_storage()
        if document_storage is None:
            continue
        if not any(
            document_storage.is_valid(
                storage_reference=evidence.storage_reference,
                requirement_id=requirement.requirement_id,
            )
            for evidence in evidence_records
        ):
            raise ConflictError(
                "Required evidence is missing or invalid.",
                code="required_evidence_invalid",
                details=[{"requirement_id": requirement.requirement_id}],
            )


def _validate_no_duplicate_application(application: Application) -> None:
    entry = (
        CatalogueEntry.objects.select_for_update()
        .filter(pk=application.catalogue_version.entry_id)
        .first()
    )
    if entry is None:
        raise NotFoundError("No such catalogue entry.")
    configuration = application.catalogue_version.configuration
    if not isinstance(configuration, dict):
        raise BadRequestError(
            "Catalogue configuration must be a JSON object.",
            code="invalid_configuration",
        )
    if configuration.get("duplicate_applications_permitted") is True:
        return
    if (
        Application.objects.filter(
            user_id=application.user_id,
            catalogue_version__entry=entry,
            academic_cycle=application.academic_cycle,
            kind="scholarship",
        )
        .exclude(pk=application.pk)
        .exclude(
            state__in=_TERMINAL_APPLICATION_STATES,
        )
        .exists()
    ):
        raise ConflictError(
            "An active application already exists for this scholarship and cycle.",
            code="duplicate_application",
        )


def _resolve_submission_transition(
    *,
    application: Application,
    to_state: str,
    guard: str,
) -> Transition:
    try:
        return resolve(
            SCHOLARSHIP_APPLICATION,
            application.state,
            to_state,
            "Student",
            guard,
        )
    except (ActorNotAllowed, AmbiguousTransition, InvalidTransition) as error:
        raise ConflictError(
            "The application cannot be submitted from its current state.",
            code="invalid_application_transition",
        ) from error


def _record_submission_transition(
    *,
    application: Application,
    user_id: int,
    transition: Transition,
) -> ApplicationTransition:
    from_state = application.state
    application.state = transition.to
    application.submitted_at = timezone.now()
    application.save(update_fields=["state", "submitted_at", "updated_at"])
    return ApplicationTransition.objects.create(
        application=application,
        from_state=from_state,
        to_state=transition.to,
        actor_user_id=user_id,
        actor_label=transition.actor,
        reason=transition.guard,
    )


def _create_submission_work(
    *,
    application: Application,
    transition: ApplicationTransition,
) -> None:
    WorkflowTask.objects.create(
        application=application,
        role_name="SPACS Assistant",
    )
    event_name = (
        "application.resubmitted"
        if transition.to_state == "Resubmitted"
        else "application.submitted"
    )
    verb = "resubmitted" if transition.to_state == "Resubmitted" else "submitted"
    verification_subject = (
        "Scholarship application requires reverification"
        if transition.to_state == "Resubmitted"
        else "Scholarship application requires verification"
    )
    verification_body = (
        f"Scholarship application {application.public_id} requires "
        f"{'re' if transition.to_state == 'Resubmitted' else ''}verification."
    )
    payload = {
        "application_id": str(application.public_id),
        "catalogue_version_id": application.catalogue_version_id,
        "state": transition.to_state,
    }
    for channel in ("email", "in_dashboard"):
        NotificationOutbox.objects.create(
            topic=event_name,
            dedupe_key=(
                f"application:{application.public_id}:transition:"
                f"{transition.pk}:user:{application.user_id}:{channel}"
            ),
            channel=channel,
            recipient_user_id=application.user_id,
            subject=(f"Scholarship application {verb}" if channel == "email" else ""),
            body=(
                f"Your scholarship application {application.public_id} was {verb}."
                if channel == "email"
                else ""
            ),
            payload=payload,
        )
        NotificationOutbox.objects.create(
            topic=event_name,
            dedupe_key=(
                f"application:{application.public_id}:transition:"
                f"{transition.pk}:role:SPACS Assistant:{channel}"
            ),
            channel=channel,
            recipient_role="SPACS Assistant",
            subject=(verification_subject if channel == "email" else ""),
            body=(verification_body if channel == "email" else ""),
            payload=payload,
        )


def _submit(
    *,
    application_id: UUID,
    user_id: int,
    to_state: str,
    guard: str,
    eligibility_evaluator: EligibilityEvaluator | None,
    document_storage: DocumentStorage | None,
) -> Application:
    application = _owned_application(
        application_id=application_id,
        user_id=user_id,
    )
    transition = _resolve_submission_transition(
        application=application,
        to_state=to_state,
        guard=guard,
    )
    if to_state == "Submitted":
        _validate_no_duplicate_application(application)
    _validate_submission(
        application=application,
        eligibility_evaluator=eligibility_evaluator,
        document_storage=document_storage,
        evaluate_eligibility=to_state == "Submitted",
    )
    transition_row = _record_submission_transition(
        application=application,
        user_id=user_id,
        transition=transition,
    )
    _create_submission_work(application=application, transition=transition_row)
    _audit_application(
        application=application,
        actor_user_id=user_id,
        event_type="application.submitted",
        payload={
            "from_state": "Correction Required"
            if to_state == "Resubmitted"
            else "Not Started / Draft",
            "to_state": to_state,
            "catalogue_version_id": application.catalogue_version_id,
        },
    )
    return application


@transaction.atomic
def submit_application(
    *,
    application_id: UUID,
    user_id: int,
    eligibility_evaluator: EligibilityEvaluator | None = None,
    document_storage: DocumentStorage | None = None,
) -> Application:
    return _submit(
        application_id=application_id,
        user_id=user_id,
        to_state="Submitted",
        guard="Submission passes eligibility, duplicate and completeness checks",
        eligibility_evaluator=eligibility_evaluator,
        document_storage=document_storage,
    )


@transaction.atomic
def resubmit_application(
    *,
    application_id: UUID,
    user_id: int,
    eligibility_evaluator: EligibilityEvaluator | None = None,
    document_storage: DocumentStorage | None = None,
) -> Application:
    return _submit(
        application_id=application_id,
        user_id=user_id,
        to_state="Resubmitted",
        guard="Resubmission passes completeness checks",
        eligibility_evaluator=eligibility_evaluator,
        document_storage=document_storage,
    )


@transaction.atomic
def export_application(
    *,
    application_id: UUID,
    actor_user_id: int,
    owner_user_id: int | None = None,
) -> dict[str, object]:
    applications = (
        Application.objects.select_for_update()
        .select_related(
            "catalogue_version",
        )
        .filter(public_id=application_id)
    )
    if owner_user_id is not None:
        applications = applications.filter(user_id=owner_user_id)
    application = applications.first()
    if application is None:
        raise NotFoundError("No such application.")
    if application.submitted_at is None:
        raise ConflictError(
            "Only submitted applications can be exported.",
            code="application_not_submitted",
        )

    transitions = list(
        ApplicationTransition.objects.filter(application=application)
        .order_by("at", "id")
        .values(
            "from_state",
            "to_state",
            "actor_user_id",
            "actor_label",
            "reason",
            "at",
        )
    )
    evidence = list(
        ApplicationEvidence.objects.filter(application=application)
        .order_by("created_at", "id")
        .values("requirement_id", "metadata", "created_at")
    )
    AuditEvent.objects.create(
        aggregate_type="application",
        aggregate_id=str(application.public_id),
        event_type="application.exported",
        actor_user_id=actor_user_id,
        actor_label="SPACS application export",
        payload={"owner_export": owner_user_id is not None},
    )
    return {
        "application": {
            "public_id": str(application.public_id),
            "kind": application.kind,
            "academic_cycle": application.academic_cycle,
            "state": application.state,
            "application_data": application.application_data,
            "submitted_at": application.submitted_at,
            "catalogue_version_id": application.catalogue_version_id,
            "policy_version": application.catalogue_version.configuration,
        },
        "transitions": transitions,
        "evidence": evidence,
    }
