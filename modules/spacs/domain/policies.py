from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationField:
    field_id: str
    name: str
    data_type: str
    required: bool
    validation: Mapping[str, object] | None = None
    display_metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class EligibilityRule:
    rule_id: str
    condition: object | None = None
    data_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    evidence_type: str
    required: bool
    applicable_condition: object | None = None
    submission: Mapping[str, object] | None = None
    verification: Mapping[str, object] | None = None


def validate_required_fields(
    fields: Sequence[ApplicationField],
    submitted_values: Mapping[str, object],
) -> list[str]:
    return [
        field.field_id
        for field in fields
        if field.required
        and (
            field.field_id not in submitted_values
            or submitted_values[field.field_id] is None
            or submitted_values[field.field_id] == ""
        )
    ]


def validate_required_evidence(
    evidence_requirements: Sequence[EvidenceRequirement],
    submitted_evidence: Collection[str],
) -> list[str]:
    return [
        requirement.requirement_id
        for requirement in evidence_requirements
        if requirement.required and requirement.requirement_id not in submitted_evidence
    ]
