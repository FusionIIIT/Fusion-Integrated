"""Placement Cell Management System (PCMS) core services with persistence.

All CRUD operations delegate to the ``repository`` module which uses SQLite via
SQLModel.  The in‑memory dictionaries from the prototype are retained only for
backwards compatibility in interactive demos.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from .models import (
    Role,
    StudentProfile,
    JobPosting,
    Application,
    ApplicationStatus,
    Interview,
    Offer,
    Announcement,
)
from . import repository
from .auth import requires_role, get_current_user

# ---------------------------------------------------------------------------
# Backwards‑compatible in‑memory stores (optional, not used by persisted API)
# ---------------------------------------------------------------------------
_student_store: Dict[str, StudentProfile] = {}
_job_store: Dict[str, JobPosting] = {}
_application_store: Dict[str, Application] = {}
_interview_store: Dict[str, Interview] = {}
_offer_store: Dict[str, Offer] = {}
_announcement_store: Dict[str, Announcement] = {}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _generate_id(prefix: str) -> str:
    """Generate a simple unique identifier using UTC timestamp.

    Format: ``{prefix}_{YYYYMMDDHHMMSSffffff}``.
    """
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

# ---------------------------------------------------------------------------
# Student profile management
# ---------------------------------------------------------------------------

@requires_role(Role.STUDENT, Role.TPO, Role.CHAIRMAN, Role.COMPANY, Role.ALUMNI)
def create_student_profile(
    student_id: str,
    name: str,
    cgpa: float,
    branch: str,
    year: int,
    skills: Optional[List[str]] = None,
    achievements: Optional[List[str]] = None,
    certifications: Optional[List[str]] = None,
    documents: Optional[List[str]] = None,
) -> StudentProfile:
    """Create or replace a student profile and persist it.

    Any caller with a recognised role may create a profile – in a real system the
    role would be restricted to the student themselves or an admin.
    """
    profile = StudentProfile(
        student_id=student_id,
        name=name,
        cgpa=cgpa,
        branch=branch,
        year=year,
        skills=skills or [],
        achievements=achievements or [],
        certifications=certifications or [],
        documents=documents or [],
    )
    _student_store[student_id] = profile
    repository.create_student(profile)
    return profile

@requires_role(Role.STUDENT, Role.TPO, Role.CHAIRMAN, Role.COMPANY, Role.ALUMNI)
def get_student_profile(student_id: str) -> Optional[StudentProfile]:
    db_obj = repository.get_student(student_id)
    if db_obj:
        return db_obj.to_dataclass()
    return _student_store.get(student_id)

# ---------------------------------------------------------------------------
# Job posting & eligibility management
# ---------------------------------------------------------------------------

@requires_role(Role.TPO, Role.COMPANY)
def create_job_posting(
    title: str,
    description: str,
    eligibility_criteria: Dict[str, any],
    deadline: datetime,
    company_id: str,
) -> JobPosting:
    """Create a new job posting and persist it.

    ``eligibility_criteria`` is stored as a JSON string in the DB.
    """
    if not all([title, description, eligibility_criteria, deadline, company_id]):
        raise ValueError("All job posting fields must be provided.")
    posting_id = _generate_id("job")
    posting = JobPosting(
        posting_id=posting_id,
        title=title,
        description=description,
        eligibility_criteria=eligibility_criteria,
        deadline=deadline,
        company_id=company_id,
    )
    _job_store[posting_id] = posting
    # Persist – convert criteria to JSON string for the SQLModel column
    posting_sql = repository.JobPostingSQL(
        posting_id=posting_id,
        title=title,
        description=description,
        eligibility_criteria=json.dumps(eligibility_criteria),
        deadline=deadline,
        company_id=company_id,
    )
    repository.create_job(posting_sql)
    return posting

@requires_role(Role.TPO, Role.COMPANY, Role.STUDENT, Role.CHAIRMAN)
def get_job_posting(posting_id: str) -> Optional[JobPosting]:
    db_obj = repository.get_job(posting_id)
    if db_obj:
        return JobPosting(
            posting_id=db_obj.posting_id,
            title=db_obj.title,
            description=db_obj.description,
            eligibility_criteria=json.loads(db_obj.eligibility_criteria),
            deadline=db_obj.deadline,
            company_id=db_obj.company_id,
        )
    return _job_store.get(posting_id)

# ---------------------------------------------------------------------------
# Eligibility check (internal helper)
# ---------------------------------------------------------------------------

def _check_eligibility(student: StudentProfile, posting: JobPosting) -> bool:
    crit = posting.eligibility_criteria
    if "min_cgpa" in crit and student.cgpa < crit["min_cgpa"]:
        return False
    if "branch" in crit:
        allowed = crit["branch"]
        if isinstance(allowed, list):
            if student.branch not in allowed:
                return False
        else:
            if student.branch != allowed:
                return False
    if "year" in crit:
        allowed = crit["year"]
        if isinstance(allowed, list):
            if student.year not in allowed:
                return False
        else:
            if student.year != allowed:
                return False
    return True

# ---------------------------------------------------------------------------
# Application submission
# ---------------------------------------------------------------------------

@requires_role(Role.STUDENT)
def submit_application(student_id: str, posting_id: str) -> Application:
    student = get_student_profile(student_id)
    posting = get_job_posting(posting_id)
    if not student:
        raise ValueError("Student profile not found.")
    if not posting:
        raise ValueError("Job posting not found.")
    if not student.is_complete():
        raise ValueError("Student profile is incomplete.")
    if not _check_eligibility(student, posting):
        raise ValueError("Student does not meet posting eligibility criteria.")
    app_id = _generate_id("app")
    application = Application(
        application_id=app_id,
        student_id=student_id,
        posting_id=posting_id,
    )
    _application_store[app_id] = application
    repository.create_application(application)
    # Notification stub
    from .notifications import notify_application_submitted
    notify_application_submitted(application)
    return application

@requires_role(Role.STUDENT, Role.TPO, Role.COMPANY, Role.CHAIRMAN)
def get_application(app_id: str) -> Optional[Application]:
    db_obj = repository.get_application(app_id)
    if db_obj:
        status = ApplicationStatus(db_obj.status)
        history = [ApplicationStatus(s) for s in db_obj.history.split(",")]
        return Application(
            application_id=db_obj.application_id,
            student_id=db_obj.student_id,
            posting_id=db_obj.posting_id,
            status=status,
            applied_at=db_obj.applied_at,
            history=history,
        )
    return _application_store.get(app_id)

# ---------------------------------------------------------------------------
# Interview scheduling
# ---------------------------------------------------------------------------

@requires_role(Role.TPO, Role.COMPANY)
def schedule_interview(
    application_id: str, scheduled_at: datetime, mode: str, details: Optional[str] = None
) -> Interview:
    if mode not in {"online", "offline"}:
        raise ValueError("Interview mode must be 'online' or 'offline'.")
    if application_id not in _application_store:
        raise ValueError("Application not found.")
    interview_id = _generate_id("int")
    interview = Interview(
        interview_id=interview_id,
        application_id=application_id,
        scheduled_at=scheduled_at,
        mode=mode,
        details=details,
    )
    _interview_store[interview_id] = interview
    repository.create_interview(interview)
    # Update application status
    app = _application_store[application_id]
    app.update_status(ApplicationStatus.INTERVIEW_SCHEDULED)
    repository.update_application_status(app.application_id, app.status.value, [s.value for s in app.history])
    # Notification stub
    from .notifications import notify_interview_scheduled
    notify_interview_scheduled(interview)
    return interview

# ---------------------------------------------------------------------------
# Offer management
# ---------------------------------------------------------------------------

@requires_role(Role.COMPANY)
def extend_offer(application_id: str, deadline: datetime) -> Offer:
    if application_id not in _application_store:
        raise ValueError("Application not found.")
    offer_id = _generate_id("offer")
    offer = Offer(
        offer_id=offer_id,
        application_id=application_id,
        deadline=deadline,
    )
    _offer_store[offer_id] = offer
    repository.create_offer(offer)
    # Update application status
    app = _application_store[application_id]
    app.update_status(ApplicationStatus.OFFER_EXTENDED)
    repository.update_application_status(app.application_id, app.status.value, [s.value for s in app.history])
    # Notification stub
    from .notifications import notify_offer_extended
    notify_offer_extended(offer)
    return offer

@requires_role(Role.STUDENT)
def respond_to_offer(offer_id: str, accept: bool) -> Offer:
    # Try DB first, fallback to in‑memory cache
    offer = _offer_store.get(offer_id) or repository.get_offer(offer_id)
    if not offer:
        raise ValueError("Offer not found.")
    if datetime.utcnow() > offer.deadline:
        raise ValueError("Offer response deadline has passed.")
    if accept:
        offer.accept()
        app = _application_store[offer.application_id]
        app.update_status(ApplicationStatus.OFFER_ACCEPTED)
        repository.update_application_status(app.application_id, app.status.value, [s.value for s in app.history])
        repository.update_offer_status(offer.offer_id, offer.status.value)
        from .notifications import notify_offer_accepted
        notify_offer_accepted(offer)
    else:
        offer.reject()
        app = _application_store[offer.application_id]
        app.update_status(ApplicationStatus.OFFER_REJECTED)
        repository.update_application_status(app.application_id, app.status.value, [s.value for s in app.history])
        repository.update_offer_status(offer.offer_id, offer.status.value)
        from .notifications import notify_offer_rejected
        notify_offer_rejected(offer)
    return offer

# ---------------------------------------------------------------------------
# Announcement handling
# ---------------------------------------------------------------------------

@requires_role(Role.TPO, Role.CHAIRMAN)
def publish_announcement(author_role: Role, title: str, content: str) -> Announcement:
    ann_id = _generate_id("ann")
    announcement = Announcement(
        announcement_id=ann_id,
        author_role=author_role,
        title=title,
        content=content,
    )
    _announcement_store[ann_id] = announcement
    repository.create_announcement(announcement)
    from .notifications import notify_announcement
    notify_announcement(announcement)
    return announcement

# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def list_student_applications(student_id: str) -> List[Application]:
    with repository.get_session() as session:
        from sqlmodel import select
        stmt = select(repository.ApplicationSQL).where(repository.ApplicationSQL.student_id == student_id)
        results = session.exec(stmt).all()
        apps: List[Application] = []
        for db_obj in results:
            status = ApplicationStatus(db_obj.status)
            history = [ApplicationStatus(s) for s in db_obj.history.split(",")]
            apps.append(
                Application(
                    application_id=db_obj.application_id,
                    student_id=db_obj.student_id,
                    posting_id=db_obj.posting_id,
                    status=status,
                    applied_at=db_obj.applied_at,
                    history=history,
                )
            )
        return apps

def list_job_postings() -> List[JobPosting]:
    with repository.get_session() as session:
        from sqlmodel import select
        stmt = select(repository.JobPostingSQL)
        results = session.exec(stmt).all()
        postings: List[JobPosting] = []
        for db_obj in results:
            postings.append(
                JobPosting(
                    posting_id=db_obj.posting_id,
                    title=db_obj.title,
                    description=db_obj.description,
                    eligibility_criteria=json.loads(db_obj.eligibility_criteria),
                    deadline=db_obj.deadline,
                    company_id=db_obj.company_id,
                )
            )
        return postings

def get_statistics() -> Dict[str, any]:
    with repository.get_session() as session:
        from sqlmodel import select
        students = session.exec(select(repository.StudentProfileSQL)).count()
        postings = session.exec(select(repository.JobPostingSQL)).count()
        applications = session.exec(select(repository.ApplicationSQL)).count()
        offers_extended = session.exec(
            select(repository.OfferSQL).where(repository.OfferSQL.status == "Offer Extended")
        ).count()
        offers_accepted = session.exec(
            select(repository.OfferSQL).where(repository.OfferSQL.status == "Offer Accepted")
        ).count()
    return {
        "students": students,
        "postings": postings,
        "applications": applications,
        "offers_extended": offers_extended,
        "offers_accepted": offers_accepted,
    }
