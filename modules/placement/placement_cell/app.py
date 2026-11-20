from pydantic import BaseModel
"""FastAPI entry point for the Placement Cell Management System (PCMS)

The API mirrors the service functions defined in ``services.py``.  It uses
Pydantic models for request bodies and returns the underlying dataclasses (which
are JSON‑serialisable because they are plain ``dataclass`` objects).
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from typing import List, Optional
from datetime import datetime

from placement_cell import services, auth
from .models import (
    Role,
    StudentProfile,
    JobPosting,
    Application,
    Interview,
    Offer,
    Announcement,
)

app = FastAPI(title="Placement Cell Management System API")

# ---------------------------------------------------------------------------
# Simple dependency that extracts a fake "X-User-Role" header and sets the
# current user for RBAC checks.  In a real system this would be a JWT token.
# ---------------------------------------------------------------------------

def get_user_role(x_user_role: Optional[str] = Header(None)) -> Role:
    if x_user_role is None:
        # default to a generic role that is allowed to call anything for the demo
        return Role.TPO
    try:
        return Role[x_user_role.upper()]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-User-Role header")

# ---------------------------------------------------------------------------
# Pydantic request schemas (lightweight wrappers around the dataclasses)
# ---------------------------------------------------------------------------

class StudentCreateSchema(StudentProfile):
    pass

class JobPostingCreateSchema(JobPosting):
    pass

class ApplicationCreateSchema(BaseModel):
    student_id: str
    posting_id: str

class InterviewCreateSchema(BaseModel):
    application_id: str
    scheduled_at: datetime
    mode: str
    details: Optional[str] = None

class OfferCreateSchema(BaseModel):
    application_id: str
    deadline: datetime

class OfferRespondSchema(BaseModel):
    accept: bool

class AnnouncementCreateSchema(Announcement):
    pass

# ---------------------------------------------------------------------------
# Endpoints – each calls the corresponding service function.  Errors from the
# service layer are turned into HTTP 400 responses.
# ---------------------------------------------------------------------------

@app.post("/students", response_model=StudentProfile)
def api_create_student(payload: StudentCreateSchema, role: Role = Depends(get_user_role)):
    try:
        return services.create_student_profile(**payload.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/students/{student_id}", response_model=StudentProfile)
def api_get_student(student_id: str, role: Role = Depends(get_user_role)):
    student = services.get_student_profile(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@app.post("/postings", response_model=JobPosting)
def api_create_job(payload: JobPostingCreateSchema, role: Role = Depends(get_user_role)):
    try:
        return services.create_job_posting(
            title=payload.title,
            description=payload.description,
            eligibility_criteria=payload.eligibility_criteria,
            deadline=payload.deadline,
            company_id=payload.company_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/postings/{posting_id}", response_model=JobPosting)
def api_get_job(posting_id: str, role: Role = Depends(get_user_role)):
    posting = services.get_job_posting(posting_id)
    if not posting:
        raise HTTPException(status_code=404, detail="Posting not found")
    return posting

@app.get("/postings", response_model=List[JobPosting])
def api_list_postings(role: Role = Depends(get_user_role)):
    return services.list_job_postings()

@app.post("/applications", response_model=Application)
def api_submit_application(payload: ApplicationCreateSchema, role: Role = Depends(get_user_role)):
    try:
        return services.submit_application(payload.student_id, payload.posting_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/applications/{app_id}", response_model=Application)
def api_get_application(app_id: str, role: Role = Depends(get_user_role)):
    app_obj = services.get_application(app_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    return app_obj

@app.get("/students/{student_id}/applications", response_model=List[Application])
def api_list_student_applications(student_id: str, role: Role = Depends(get_user_role)):
    return services.list_student_applications(student_id)

@app.post("/interviews", response_model=Interview)
def api_schedule_interview(payload: InterviewCreateSchema, role: Role = Depends(get_user_role)):
    try:
        return services.schedule_interview(
            payload.application_id, payload.scheduled_at, payload.mode, payload.details
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/offers", response_model=Offer)
def api_extend_offer(payload: OfferCreateSchema, role: Role = Depends(get_user_role)):
    try:
        return services.extend_offer(payload.application_id, payload.deadline)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/offers/{offer_id}/respond", response_model=Offer)
def api_respond_offer(offer_id: str, payload: OfferRespondSchema, role: Role = Depends(get_user_role)):
    try:
        return services.respond_to_offer(offer_id, payload.accept)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/announcements", response_model=Announcement)
def api_publish_announcement(payload: AnnouncementCreateSchema, role: Role = Depends(get_user_role)):
    try:
        return services.publish_announcement(payload.author_role, payload.title, payload.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/statistics", response_model=dict)
def api_statistics(role: Role = Depends(get_user_role)):
    return services.get_statistics()
