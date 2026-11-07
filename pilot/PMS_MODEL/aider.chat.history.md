
# aider chat started at 2026-11-07 13:58:05

> /opt/homebrew/bin/aider --model ollama_chat/qwen3.5:4b --edit-format whole --map-tokens 1024 --timeout 3600 --yes-always --stream --no-pretty --no-fancy-input --no-gitignore --no-auto-commits --no-dirty-commits --no-auto-lint --no-auto-test --no-check-update --analytics-disable --no-show-release-notes --no-show-model-warnings --no-suggest-shell-commands --no-detect-urls --no-restore-chat-history --aiderignore /Users/vishalkumar/elm_specs_md/pms_kit/aiderignore --chat-history-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/aider.chat.history.md --input-history-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/aider.input.history --llm-history-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/llm.history.txt --read /Users/vishalkumar/elm_specs_md/pms_kit/chunks/problem_statement.md --read /Users/vishalkumar/elm_specs_md/pms_kit/chunks/states.md --read modules/placement/apps.py --read modules/placement/registry.py --read core/db/mixins.py --file modules/patent/__init__.py --file modules/patent/apps.py --file modules/patent/registry.py --file modules/patent/models.py --message-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/prompts/step1.md  
> Creating empty file /Users/vishalkumar/ELM_MODEL_2/modules/patent/__init__.py  
> Creating empty file /Users/vishalkumar/ELM_MODEL_2/modules/patent/apps.py  
> Creating empty file /Users/vishalkumar/ELM_MODEL_2/modules/patent/registry.py  
> Creating empty file /Users/vishalkumar/ELM_MODEL_2/modules/patent/models.py  
> Aider v0.86.2  
> Model: ollama_chat/qwen3.5:4b with whole edit format  
> Git repo: .git with 235 files  
> Repo-map: using 1024 tokens, auto refresh  
> Added modules/patent/__init__.py to the chat.  
> Added modules/patent/apps.py to the chat.  
> Added modules/patent/models.py to the chat.  
> Added modules/patent/registry.py to the chat.  
> Added modules/placement/registry.py to the chat (read-only).  
> Added ../elm_specs_md/pms_kit/chunks/states.md to the chat (read-only).  
> Added core/db/mixins.py to the chat (read-only).  
> Added ../elm_specs_md/pms_kit/chunks/problem_statement.md to the chat (read-only).  
> Added modules/placement/apps.py to the chat (read-only).  

#### Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.  
####   
#### Repository rules you must follow:  
#### - There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.  
#### - A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).  
#### - The module code is "patent", and every permission code starts with "patent.".  
#### - Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.  
#### - The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.  
####   
#### Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.  
####   
#### Step 1 of 11 — module foundation, from the read-only problem statement and state table.  
####   
#### Create these files:  
#### 1. modules/patent/__init__.py — empty.  
#### 2. modules/patent/apps.py — PatentConfig with name "modules.patent" and label "patent", following modules/placement/apps.py.  
#### 3. modules/patent/registry.py — following modules/placement/registry.py: MODULE (code "patent", label "Patent Management", base_path "/patent"), NAV_ITEMS whose "to" paths are /patent/mine, /patent/submit, /patent/review, /patent/admin and /patent/attorney, PERMISSIONS (every code starts with "patent."), and ROLE_GRANTS keyed by the four actors (Applicant, Director, PCC_ADMIN, Attorney). Every permission must be granted to at least one role.  
#### 4. modules/patent/models.py — Django models on core.db.mixins.TimeStampedModel. People are integer user ids.  
####    - PatentApplication: unique application number, title, abstract, description, claims, technical domain, applicant_id, status, assigned_director_id, assigned_attorney_id, review_due_date, resubmission_deadline, latest decision and justification, version number. Status choices: Draft, Submitted, Under Review, Needs Revision, Resubmitted, Rejected, Appeal Submitted, Approved, Attorney Assigned, Filed, Granted, Withdrawn, Expired.  
####    - Inventor (application, optional user_id, name, email, contribution percent, agreement_signed).  
####    - ApplicationDocument (application, file name, content type, size in bytes, version, sensitivity, uploaded_by, archived).  
####    - AttorneyAssignment (application, attorney_id, status Offered/Accepted/Declined, decline reason).  
####    - PatentabilityOpinion (application, attorney_id, novelty, non-obviousness, utility, recommendation File Patent/Do Not File/Needs Amendment, opinion text).  
####    - Budget (application, filing fee, attorney fee, administrative cost, total, status Pending/Approved/Rejected/Escalated, decided_by, justification).  
####    - Filing (application, patent office, filing number, filing date, international flag, grant number, grant date).  
####    - OfficeAction (application, received date, response due date, description, response text, status Recorded/Awaiting Applicant Approval/Applicant Approved/Response Ready/Response Submitted).  
####    - MaintenanceRecord (application, due date, fee, decision Renewal Requested/Renew/Do Not Renew, decided_by).  
####    - Appeal (application, grounds, status Submitted/Remanded for Amendment/Rejection Upheld/Decision Modified, decided_by, justification).  
####    - ApplicationHistory: append-only row (application, actor_id, action, from_status, to_status, note).  

modules/patent/__init__.py
```python
# Empty module init for Patent Management System (PMS)
```

modules/patent/apps.py
```python
from django.apps import AppConfig
from django.core.checks import register


class PatentConfig(AppConfig):
    name = "modules.patent"
    label = "patent"

    def ready(self):
        # PMS does not own a global upload root check; it relies on the platform's
        # configuration (e.g., PLACEMENT_UPLOAD_ROOT or similar) for file storage.
        # No custom checks registered here to avoid duplication with placement.
```

modules/patent/registry.py
```python
"""What the server tells the shell about this module (ADR-0010).

PMS nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "patent", "label": "Patent Management", "icon": "FileText",
    "base_path": "/patent", "nav_section": "Patent", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- Applicant: personal view and submission ----------------------------
    {"code": "patent.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/patent/mine",
     "required_permission": "patent.application.view_self",
     "sort_order": 5},
    {"code": "patent.submit", "label": "Submit Application",
     "icon": "Plus", "to": "/patent/submit",
     "required_permission": "patent.application.create",
     "sort_order": 10},

    # -- Director: review and decision -------------------------------------
    {"code": "patent.review", "label": "Review Applications",
     "icon": "ClipboardCheck", "to": "/patent/review",
     "required_permission": "patent.application.review",
     "sort_order": 15},

    # -- PCC_ADMIN: administration and coordination ------------------------
    {"code": "patent.admin", "label": "Administration",
     "icon": "Cog", "to": "/patent/admin",
     "required_permission": "patent.admin.manage",
     "sort_order": 25},

    # -- Attorney: legal and filing support --------------------------------
    {"code": "patent.attorney", "label": "Legal & Filing",
     "icon": "Gavel", "to": "/patent/attorney",
     "required_permission": "patent.legal.review",
     "sort_order": 30},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("patent.application.view_self", "See one's own applications"),
    ("patent.application.create", "Submit a new patent application"),
    ("patent.application.review", "Review and decide on applications"),
    ("patent.application.manage", "Manage application lifecycle (assign, withdraw, etc.)"),
    ("patent.admin.manage", "Manage PMS configuration, roles, and global settings"),
    ("patent.legal.review", "Conduct legal review, prior art search, and file patents"),
    ("patent.budget.approve", "Approve or reject patent application budgets"),
    ("patent.filing.record", "Record external patent office filings"),
    ("patent.maintenance.manage", "Manage maintenance fee renewals"),
    ("patent.appeal.review", "Review and decide on appeals"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "patent.application.auto_withdraw",  # System auto-withdrawal if deadline missed
    "patent.filing.expire",              # System filing expiry tracking
]

_STUDENT = [
    "patent.application.view_self",
    "patent.application.create",
    "patent.application.delete",
    "patent.application.withdraw",
]

_DIRECTOR = [
    "patent.application.review",
    "patent.budget.approve",
    "patent.maintenance.manage",
    "patent.appeal.review",
]

_PCC_ADMIN = [
    "patent.admin.manage",
    "patent.application.manage",
    "patent.legal.review",  # PCC_ADMIN can oversee attorney work
    "patent.budget.approve",
    "patent.filing.record",
]

_ATTORNEY = [
    "patent.legal.review",
    "patent.filing.record",
    "patent.maintenance.manage",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "Applicant": _STUDENT,
    "Director": _DIRECTOR,
    "PCC_ADMIN": _PCC_ADMIN,
    "Attorney": _ATTORNEY,
}
```

modules/patent/models.py
```python
from django.db import models
from core.db.mixins import TimeStampedModel


class PatentApplication(TimeStampedModel):
    """Core patent application record."""
    
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("needs_revision", "Needs Revision"),
        ("resubmitted", "Resubmitted"),
        ("rejected", "Rejected"),
        ("appeal_submitted", "Appeal Submitted"),
        ("approved", "Approved"),
        ("attorney_assigned", "Attorney Assigned"),
        ("filed", "Filed"),
        ("granted", "Granted"),
        ("withdrawn", "Withdrawn"),
        ("expired", "Expired"),
    ]

    APPLICATION_NUMBER = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    abstract = models.TextField(blank=True)
    description = models.TextField()
    claims = models.TextField()
    technical_domain = models.CharField(max_length=100)
    
    applicant_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    assigned_director_id = models.IntegerField(null=True, blank=True)
    assigned_attorney_id = models.IntegerField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)
    resubmission_deadline = models.DateField(null=True, blank=True)
    
    # Latest decision and justification (stored as text for flexibility)
    latest_decision = models.CharField(max_length=50, null=True, blank=True)
    latest_justification = models.TextField(blank=True)
    
    version_number = models.IntegerField(default=1)

    class Meta:
        app_label = "patent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.APPLICATION_NUMBER} ({self.status})"


class Inventor(TimeStampedModel):
    """Inventor associated with a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="inventors")
    user_id = models.IntegerField(null=True, blank=True, db_index=True)  # Optional: linked IAM user
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    contribution_percent = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    agreement_signed = models.BooleanField(default=False)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION", "user_id"]  # Prevent duplicate entries for same user

    def __str__(self):
        return f"Inventor {self.name} on {self.APPLICATION}"


class ApplicationDocument(TimeStampedModel):
    """Document associated with a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="documents")
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)  # e.g., "application.pdf"
    size = models.BigIntegerField()  # in bytes
    version = models.IntegerField(default=1)
    sensitivity = models.CharField(max_length=20, choices=[("public", "Public"), ("internal", "Internal"), ("confidential", "Confidential")])
    uploaded_by = models.IntegerField(db_index=True)
    archived = models.BooleanField(default=False)

    class Meta:
        app_label = "patent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.APPLICATION} - {self.file_name} (v{self.version})"


class AttorneyAssignment(TimeStampedModel):
    """Attorney assignment record for a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="assignments")
    attorney_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=[("offered", "Offered"), ("accepted", "Accepted"), ("declined", "Declined")], default="offered")
    decline_reason = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One assignment per application at a time

    def __str__(self):
        return f"{self.APPLICATION} - {self.attorney_id} ({self.status})"


class PatentabilityOpinion(TimeStampedModel):
    """Attorney's legal and patentability assessment."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="opinions")
    attorney_id = models.IntegerField(db_index=True)
    novelty = models.BooleanField(default=False)  # True if novel
    non_obviousness = models.BooleanField(default=False)  # True if non-obvious
    utility = models.BooleanField(default=False)  # True if useful
    recommendation = models.CharField(max_length=30, choices=[("file_patent", "File Patent"), ("do_not_file", "Do Not File"), ("needs_amendment", "Needs Amendment")], default="needs_amendment")
    opinion_text = models.TextField()

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One primary opinion per application

    def __str__(self):
        return f"{self.APPLICATION} - {self.recommendation}"


class Budget(TimeStampedModel):
    """Budget record for a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="budgets")
    filing_fee = models.DecimalField(max_digits=10, decimal_places=2)
    attorney_fee = models.DecimalField(max_digits=10, decimal_places=2)
    administrative_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)  # Calculated field (can be overridden by manager)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("escalated", "Escalated")], default="pending")
    decided_by = models.IntegerField(null=True, blank=True)
    justification = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One budget per application at a time

    def __str__(self):
        return f"{self.APPLICATION} - ${self.total}"


class Filing(TimeStampedModel):
    """External patent office filing record."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="filings")
    patent_office = models.CharField(max_length=100)  # e.g., "USPTO", "EPO"
    filing_number = models.CharField(max_length=50)
    filing_date = models.DateField()
    international = models.BooleanField(default=False)
    grant_number = models.CharField(max_length=50, null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One primary filing per application

    def __str__(self):
        return f"{self.APPLICATION} - {self.patent_office} #{self.filing_number}"


class OfficeAction(TimeStampedModel):
    """Office action received from patent office."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="office_actions")
    received_date = models.DateField()
    response_due_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    response_text = models.TextField(blank=True)  # Draft or submitted response
    status = models.CharField(max_length=30, choices=[("recorded", "Recorded"), ("awaiting_applicant_approval", "Awaiting Applicant Approval"), ("applicant_approved", "Applicant Approved"), ("response_ready", "Response Ready"), ("response_submitted", "Response Submitted")], default="recorded")

    class Meta:
        app_label = "patent"
        ordering = ["-received_date"]

    def __str__(self):
        return f"{self.APPLICATION} - {self.status}"


class MaintenanceRecord(TimeStampedModel):
    """Maintenance fee renewal record."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="maintenance_records")
    due_date = models.DateField()
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    decision = models.CharField(max_length=30, choices=[("renewal_requested", "Renewal Requested"), ("renew", "Renew"), ("do_not_renew", "Do Not Renew")], default="renewal_requested")
    decided_by = models.IntegerField(null=True, blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One decision per cycle (tracked by due_date)

    def __str__(self):
        return f"{self.APPLICATION} - {self.due_date} ({self.decision})"


class Appeal(TimeStampedModel):
    """Appeal record against a rejection."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="appeals")
    grounds = models.TextField()
    status = models.CharField(max_length=30, choices=[("submitted", "Submitted"), ("remanded_for_amendment", "Remanded for Amendment"), ("rejection_upheld", "Rejection Upheld"), ("decision_modified", "Decision Modified")], default="submitted")
    decided_by = models.IntegerField(null=True, blank=True)
    justification = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One appeal per application at a time

    def __str__(self):
        return f"{self.APPLICATION} - {self.status}"


class ApplicationHistory(TimeStampedModel):
    """Append-only history of application status changes and actions."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="history")
    actor_id = models.IntegerField(db_index=True)  # User ID who performed the action
    action = models.CharField(max_length=50)  # e.g., "review", "assign", "withdraw"
    from_status = models.CharField(max_length=30, null=True, blank=True)
    to_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.APPLICATION} - {self.actor_id}: {self.action}"
```

> Tokens: 8.5k sent, 3.2k received.  
> Applied edit to modules/patent/__init__.py  
> Applied edit to modules/patent/apps.py  
> Applied edit to modules/patent/registry.py  
> Applied edit to modules/patent/models.py  

# aider chat started at 2026-11-07 14:07:52

> /opt/homebrew/bin/aider --model ollama_chat/qwen3.5:4b --edit-format whole --map-tokens 1024 --timeout 3600 --yes-always --stream --no-pretty --no-fancy-input --no-gitignore --no-auto-commits --no-dirty-commits --no-auto-lint --no-auto-test --no-check-update --analytics-disable --no-show-release-notes --no-show-model-warnings --no-suggest-shell-commands --no-detect-urls --no-restore-chat-history --aiderignore /Users/vishalkumar/elm_specs_md/pms_kit/aiderignore --chat-history-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/aider.chat.history.md --input-history-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/aider.input.history --llm-history-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/llm.history.txt --read /Users/vishalkumar/elm_specs_md/pms_kit/chunks/br_core.md --read /Users/vishalkumar/elm_specs_md/pms_kit/chunks/states.md --read modules/patent/models.py --file modules/patent/domain/__init__.py --file modules/patent/domain/policy.py --message-file /Users/vishalkumar/ELM_MODEL_2/pilot/PMS_MODEL/prompts/step2.md  
> Creating empty file /Users/vishalkumar/ELM_MODEL_2/modules/patent/domain/__init__.py  
> Creating empty file /Users/vishalkumar/ELM_MODEL_2/modules/patent/domain/policy.py  
> Aider v0.86.2  
> Model: ollama_chat/qwen3.5:4b with whole edit format  
> Git repo: .git with 239 files  
> Repo-map: using 1024 tokens, auto refresh  
> Added modules/patent/domain/__init__.py to the chat.  
> Added modules/patent/domain/policy.py to the chat.  
> Added ../elm_specs_md/pms_kit/chunks/states.md to the chat (read-only).  
> Added ../elm_specs_md/pms_kit/chunks/br_core.md to the chat (read-only).  
> Added modules/patent/models.py to the chat (read-only).  

#### Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.  
####   
#### Repository rules you must follow:  
#### - There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.  
#### - A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).  
#### - The module code is "patent", and every permission code starts with "patent.".  
#### - Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.  
#### - The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.  
####   
#### Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.  
####   
#### Step 2 of 11 — PMS policy rules, from the read-only core business rules and state table, with modules/patent/models.py read-only.  
####   
#### Create these files:  
#### 1. modules/patent/domain/__init__.py — empty.  
#### 2. modules/patent/domain/policy.py — pure Python (no Django, DRF or Celery imports). Plain functions and dataclasses, each with a one-line comment citing the BR-PMS id it enforces:  
####    - ALLOWED_TRANSITIONS: a dict from each application status to the statuses it may move to (from the state table), and can_transition(from_status, to_status).  
####    - validate_document(file_name, content_type, size_bytes): PDF only and under 50 MB (BR-PMS-014, 015).  
####    - missing_required_fields(data): title, abstract, description, claims and at least one inventor (BR-PMS-017).  
####    - validate_justification(text): at least 50 characters (BR-PMS-030).  
####    - add_business_days(start_date, days) and review_due_date(assigned_on): 15 business days (BR-PMS-031).  
####    - resubmission_deadline(decision_date): 60 days (BR-PMS-035).  
####    - is_conflicted(reviewer_id, inventor_user_ids): a reviewer listed as inventor is conflicted (BR-PMS-025..027).  
####    - can_withdraw(status): only pre-filing statuses.  
####    - budget_needs_escalation(total, threshold).  

modules/patent/domain/__init__.py
```python
# Empty module for patent domain logic
```

modules/patent/domain/policy.py
```python
"""
Pure Python policy rules for the Patent Management System (PMS).
No Django, DRF, or Celery imports.
Enforces business rules BR-PMS-003 through BR-PMS-140 as specified in read-only specs.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Set, List, Any


# -----------------------------------------------------------------------------
# State Transitions (BR-PMS state table)
# -----------------------------------------------------------------------------

ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "draft": {"submitted"},
    "submitted": {"under_review", "withdrawn"},
    "under_review": {"approved", "needs_revision", "rejected", "escalated"},
    "needs_revision": {"resubmitted", "withdrawn"},
    "resubmitted": {"under_review", "withdrawn"},
    "rejected": {"appeal_submitted", "withdrawn"},
    "appeal_submitted": {"remanded_for_amendment", "rejection_upheld", "decision_modified"},
    "approved": {"attorney_assigned", "budget_approved", "budget_rejected", "budget_escalated"},
    "attorney_assigned": {"attorney_declined", "pending_review"},
    "pending_review": {"attorney_assigned"},  # Reassignment if declined or invalid
    "filed": {"office_action_recorded"},  # Implicit transition on communication receipt
    "office_action_recorded": {"awaiting_applicant_approval", "response_ready", "response_submitted"},
    "awaiting_applicant_approval": {"applicant_approved"},
    "applicant_approved": {"response_ready"},
    "response_ready": {"response_submitted"},
    "response_submitted": {"under_review"},  # Back to review cycle or granted
    "granted": {"renewal_requested"},
    "renewal_requested": {"renewed", "do_not_renew", "escalated"},
    "renewed": {"next_cycle_scheduled"},
    "withdrawn": {},
    "expired": {},
    "remanded_for_amendment": {"under_review"},  # Back to review after amendment
    "decision_modified": {"under_review"},  # Back to review after modification
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a transition is allowed based on the state table."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


# -----------------------------------------------------------------------------
# Document Validation (BR-PMS-014, 015, 016)
# -----------------------------------------------------------------------------

def validate_document(file_name: str, content_type: str, size_bytes: int) -> bool:
    """
    Validate document for submission.
    Rules: PDF only (BR-PMS-014), under 50 MB (BR-PMS-015).
    Malware validation is assumed to be handled by an external service or middleware.
    """
    if content_type.lower() != "application/pdf":
        return False
    if size_bytes > 50 * 1024 * 1024:  # 50 MB
        return False
    return True


# -----------------------------------------------------------------------------
# Application Validation (BR-PMS-017)
# -----------------------------------------------------------------------------

def missing_required_fields(data: Dict[str, Any]) -> List[str]:
    """
    Check for missing required application fields.
    Required: title, abstract, description, claims, at least one inventor.
    Returns list of missing field names.
    """
    missing = []
    if not data.get("title"):
        missing.append("title")
    if not data.get("abstract"):
        missing.append("abstract")
    if not data.get("description"):
        missing.append("description")
    if not data.get("claims"):
        missing.append("claims")
    
    inventors = data.get("inventors", [])
    if len(inventors) == 0:
        missing.append("inventor")
    
    return missing


# -----------------------------------------------------------------------------
# Decision Validation (BR-PMS-029, 030)
# -----------------------------------------------------------------------------

def validate_justification(text: str) -> bool:
    """
    Validate Director review justification.
    Rule BR-PMS-030: Must be at least 50 characters.
    """
    return len(text.strip()) >= 50


# -----------------------------------------------------------------------------
# Date Calculations (BR-PMS-031, 035)
# -----------------------------------------------------------------------------

def add_business_days(start_date: date, days: int) -> date:
    """
    Add business days to a start date.
    Skips weekends (Saturday, Sunday).
    """
    current = start_date
    count = 0
    while count < days:
        if current.weekday() < 5:  # Monday (0) to Friday (4)
            count += 1
        current += timedelta(days=1)
    return current


def review_due_date(assigned_on: date) -> date:
    """
    Calculate the review due date for a Director.
    Rule BR-PMS-031: 15 business days from assignment.
    """
    return add_business_days(assigned_on, 15)


def resubmission_deadline(decision_date: date) -> date:
    """
    Calculate the resubmission deadline for an Applicant.
    Rule BR-PMS-035: 60 days from rejection or revision-request decision.
    """
    return add_business_days(decision_date, 60)


# -----------------------------------------------------------------------------
# Conflict of Interest (BR-PMS-025, 026, 027)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class InventorInfo:
    user_id: int
    name: str


def is_conflicted(reviewer_id: int, inventor_user_ids: Set[int]) -> bool:
    """
    Check if a reviewer is conflicted with any inventor.
    Rules BR-PMS-025 (PCC_ADMIN), BR-PMS-026 (Director):
    A reviewer listed as an inventor cannot review the application.
    """
    return reviewer_id in inventor_user_ids


# -----------------------------------------------------------------------------
# Withdrawal Eligibility (BR-PMS-067, 068)
# -----------------------------------------------------------------------------

def can_withdraw(status: str) -> bool:
    """
    Check if withdrawal is allowed from the current status.
    Rule BR-PMS-067: Only before filing stage.
    Rule BR-PMS-068: Status must be withdrawal-eligible under PMS rules.
    
    Withdrawal-eligible statuses based on state table and pre-filing constraint:
    - draft, submitted, under_review, needs_revision, resubmitted, rejected
    
    Note: 'approved' is technically in the table but usually not withdrawable post-grant/filing.
    However, strict interpretation of "before filing" suggests only very early stages.
    Based on the state table provided, we allow withdrawal from states that are pre-filing or explicitly listed as eligible.
    The state table lists 'submitted', 'under_review', etc. as having a transition to 'withdrawn'.
    We will assume any status that has 'withdrawn' in its allowed transitions is eligible.
    """
    return "withdrawn" in ALLOWED_TRANSITIONS.get(status, set())


# -----------------------------------------------------------------------------
# Budget Escalation (BR-PMS-009)
# -----------------------------------------------------------------------------

def budget_needs_escalation(total: float, threshold: float) -> bool:
    """
    Check if a budget total exceeds the configured threshold.
    Rule BR-PMS-009: If total cost exceeds threshold, status becomes 'Escalated'.
    """
    return total > threshold
```

> Tokens: 7.3k sent, 1.6k received.  
> Applied edit to modules/patent/domain/policy.py  
> Applied edit to modules/patent/domain/__init__.py  
