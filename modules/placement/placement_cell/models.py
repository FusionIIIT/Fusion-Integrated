"""Models for Placement Cell Management System (PCMS)"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Role(Enum):
    STUDENT = "Student"
    TPO = "Training and Placement Officer"
    CHAIRMAN = "Placement Chairman"
    COMPANY = "Company/Recruiter"
    ALUMNI = "Alumni"


class ApplicationStatus(Enum):
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    INTERVIEW_SCHEDULED = "Interview Scheduled"
    OFFER_EXTENDED = "Offer Extended"
    OFFER_ACCEPTED = "Offer Accepted"
    OFFER_REJECTED = "Offer Rejected"
    REJECTED = "Rejected"


@dataclass
class StudentProfile:
    student_id: str
    name: str
    cgpa: float
    branch: str
    year: int
    skills: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        return bool(self.skills) and bool(self.documents)


@dataclass
class JobPosting:
    posting_id: str
    title: str
    description: str
    eligibility_criteria: dict
    deadline: datetime
    company_id: str


@dataclass
class Application:
    application_id: str
    student_id: str
    posting_id: str
    status: ApplicationStatus = ApplicationStatus.APPLIED
    applied_at: datetime = field(default_factory=datetime.utcnow)
    history: List[ApplicationStatus] = field(default_factory=lambda: [ApplicationStatus.APPLIED])

    def update_status(self, new_status: ApplicationStatus):
        self.status = new_status
        self.history.append(new_status)


@dataclass
class Interview:
    interview_id: str
    application_id: str
    scheduled_at: datetime
    mode: str
    details: Optional[str] = None


@dataclass
class Offer:
    offer_id: str
    application_id: str
    offered_at: datetime = field(default_factory=datetime.utcnow)
    deadline: datetime = field(default=None)
    status: ApplicationStatus = ApplicationStatus.OFFER_EXTENDED

    def accept(self):
        self.status = ApplicationStatus.OFFER_ACCEPTED

    def reject(self):
        self.status = ApplicationStatus.OFFER_REJECTED


@dataclass
class Announcement:
    announcement_id: str
    author_role: Role
    title: str
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
