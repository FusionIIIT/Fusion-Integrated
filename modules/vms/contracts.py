"""Cross-module and boundary contracts for the VMS module (ADR-0010/ADR-0013)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class PreRegisterDTO:
    visitor_name: str
    visitor_phone: str
    visitor_email: str
    id_doc_type: str
    id_doc_number: str
    organization: str
    host_id: int
    purpose: str
    scheduled_start: datetime
    scheduled_end: datetime
    remarks: str = ""


@dataclass(frozen=True)
class HostDecisionDTO:
    request_id: str
    host_id: int
    outcome: str  # "APPROVE" | "REJECT"
    allowed_start: Optional[datetime] = None
    allowed_end: Optional[datetime] = None
    permitted_zones: Optional[List[str]] = None
    special_instructions: str = ""


@dataclass(frozen=True)
class GateValidationDTO:
    credential_data: str
    gate_id: str
    verifier_id: int
    verifier_notes: str = ""


@dataclass(frozen=True)
class GateCheckoutDTO:
    pass_id: str
    gate_id: str
    verifier_id: int
    verifier_notes: str = ""


@dataclass(frozen=True)
class ValidationVerdictDTO:
    allowed: bool
    reason: str
    visitor_name: Optional[str] = None
    pass_id: Optional[str] = None
    pass_status: Optional[str] = None
    permitted_zones: Optional[List[str]] = None
    visit_id: Optional[str] = None
