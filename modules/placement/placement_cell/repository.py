"""SQLModel based repository for PCMS persistent storage.

The models mirror those defined in ``models.py`` but inherit from ``SQLModel``
so they can be persisted in an SQLite database (``pcms.db``) located in the same
directory.  Simple CRUD helpers are provided; the service layer imports and uses
these helpers.
"""

from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite:///pcms.db"
engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Create tables if they do not exist."""
    SQLModel.metadata.create_all(engine)

# ---------------------------------------------------------------------------
# Persistent models (SQLModel)
# ---------------------------------------------------------------------------

class StudentProfileSQL(SQLModel, table=True):
    student_id: str = Field(primary_key=True)
    name: str
    cgpa: float
    branch: str
    year: int
    skills: str = Field(default="")  # comma‑separated
    achievements: str = Field(default="")
    certifications: str = Field(default="")
    documents: str = Field(default="")
    # Helper to convert to the dataclass defined in models.py
    def to_dataclass(self):
        from .models import StudentProfile
        return StudentProfile(
            student_id=self.student_id,
            name=self.name,
            cgpa=self.cgpa,
            branch=self.branch,
            year=self.year,
            skills=self.skills.split(",") if self.skills else [],
            achievements=self.achievements.split(",") if self.achievements else [],
            certifications=self.certifications.split(",") if self.certifications else [],
            documents=self.documents.split(",") if self.documents else [],
        )

class JobPostingSQL(SQLModel, table=True):
    posting_id: str = Field(primary_key=True)
    title: str
    description: str
    eligibility_criteria: str  # JSON string for simplicity
    deadline: datetime
    company_id: str

class ApplicationSQL(SQLModel, table=True):
    application_id: str = Field(primary_key=True)
    student_id: str
    posting_id: str
    status: str = Field(default="Applied")
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    # History stored as JSON list of strings
    history: str = Field(default="[\"Applied\"]")

class InterviewSQL(SQLModel, table=True):
    interview_id: str = Field(primary_key=True)
    application_id: str
    scheduled_at: datetime
    mode: str
    details: Optional[str] = None

class OfferSQL(SQLModel, table=True):
    offer_id: str = Field(primary_key=True)
    application_id: str
    offered_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: datetime
    status: str = Field(default="Offer Extended")

class AnnouncementSQL(SQLModel, table=True):
    announcement_id: str = Field(primary_key=True)
    author_role: str
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ---------------------------------------------------------------------------
# CRUD helpers used by the service layer
# ---------------------------------------------------------------------------

def get_session() -> Session:
    return Session(engine)

# Student helpers
def create_student(profile) -> StudentProfileSQL:
    with get_session() as session:
        db_obj = StudentProfileSQL(
            student_id=profile.student_id,
            name=profile.name,
            cgpa=profile.cgpa,
            branch=profile.branch,
            year=profile.year,
            skills=",".join(profile.skills),
            achievements=",".join(profile.achievements),
            certifications=",".join(profile.certifications),
            documents=",".join(profile.documents),
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

def get_student(student_id: str) -> Optional[StudentProfileSQL]:
    with get_session() as session:
        return session.get(StudentProfileSQL, student_id)

# Job posting helpers
def create_job(posting) -> JobPostingSQL:
    with get_session() as session:
        db_obj = JobPostingSQL(
            posting_id=posting.posting_id,
            title=posting.title,
            description=posting.description,
            eligibility_criteria=posting.eligibility_criteria,
            deadline=posting.deadline,
            company_id=posting.company_id,
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

def get_job(posting_id: str) -> Optional[JobPostingSQL]:
    with get_session() as session:
        return session.get(JobPostingSQL, posting_id)

# Application helpers
def create_application(app) -> ApplicationSQL:
    with get_session() as session:
        db_obj = ApplicationSQL(
            application_id=app.application_id,
            student_id=app.student_id,
            posting_id=app.posting_id,
            status=app.status.value,
            applied_at=app.applied_at,
            history=",".join([s.value for s in app.history]),
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

def get_application(app_id: str) -> Optional[ApplicationSQL]:
    with get_session() as session:
        return session.get(ApplicationSQL, app_id)

def update_application_status(app_id: str, new_status: str, history: List[str]):
    with get_session() as session:
        obj = session.get(ApplicationSQL, app_id)
        if obj:
            obj.status = new_status
            obj.history = ",".join(history)
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

# Interview helpers
def create_interview(interview) -> InterviewSQL:
    with get_session() as session:
        db_obj = InterviewSQL(
            interview_id=interview.interview_id,
            application_id=interview.application_id,
            scheduled_at=interview.scheduled_at,
            mode=interview.mode,
            details=interview.details,
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

# Offer helpers
def create_offer(offer) -> OfferSQL:
    with get_session() as session:
        db_obj = OfferSQL(
            offer_id=offer.offer_id,
            application_id=offer.application_id,
            offered_at=offer.offered_at,
            deadline=offer.deadline,
            status=offer.status.value,
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

def get_offer(offer_id: str) -> Optional[OfferSQL]:
    with get_session() as session:
        return session.get(OfferSQL, offer_id)

def update_offer_status(offer_id: str, new_status: str):
    with get_session() as session:
        obj = session.get(OfferSQL, offer_id)
        if obj:
            obj.status = new_status
            session.add(obj)
            session.commit()
            session.refresh(obj)
        return obj

# Announcement helpers
def create_announcement(announcement) -> AnnouncementSQL:
    with get_session() as session:
        db_obj = AnnouncementSQL(
            announcement_id=announcement.announcement_id,
            author_role=announcement.author_role.value,
            title=announcement.title,
            content=announcement.content,
            created_at=announcement.created_at,
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

def list_announcements() -> List[AnnouncementSQL]:
    with get_session() as session:
        statement = select(AnnouncementSQL)
        results = session.exec(statement).all()
        return results

# Initialise DB on import
init_db()
