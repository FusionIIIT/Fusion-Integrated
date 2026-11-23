from drf_spectacular.utils import OpenApiExample

from modules.lms.api import serializers as s

AT = "2026-11-23T09:00:00Z"
MATERIAL = {
    "id": 1,
    "workspace_id": 1,
    "section_id": None,
    "title": "Lesson",
    "kind": "NOTE",
    "text": "Read chapter one",
    "url": "",
    "file": None,
    "order": 0,
    "state": "DRAFT",
    "release_at": None,
    "published_at": None,
    "author_user_id": 1,
}
ASSIGNMENT = {
    "id": 1,
    "workspace_id": 1,
    "title": "Exercise",
    "instructions": "Explain the result",
    "due_at": "2026-12-01T09:00:00Z",
    "submission_type": "TEXT",
    "points_possible": "20.00",
    "state": "DRAFT",
    "release_at": None,
    "published_at": None,
    "author_user_id": 1,
}
SUBMISSION = {
    "id": 1,
    "assignment_id": 1,
    "user_id": 2,
    "kind": "TEXT",
    "text": "My answer",
    "url": "",
    "file": None,
    "submitted_at": AT,
    "policy_version": "A9-LMS-BP-0.2",
}
GRADE = {
    "id": 1,
    "submission_id": 1,
    "assignment_id": 1,
    "user_id": 2,
    "points": "15.00",
    "feedback": "Explain your reasoning",
    "state": "DRAFT",
    "grader_user_id": 1,
    "graded_at": AT,
    "released_by_user_id": None,
    "released_at": None,
}
VALUES = {
    s.CourseSerializer: {
        "id": 1,
        "external_offering_key": "cof_" + "a" * 64,
        "course_code": "SYN101",
        "course_name": "Synthetic Course",
        "working_year": "2026",
        "session": "AUTUMN",
        "syllabus": "Course overview",
        "schedule": "Monday",
        "details_published_at": AT,
        "acting_course_role": "FACULTY",
        "can_post_announcements": True,
        "staff": [],
        "sections": [],
    },
    s.CourseInput: {"syllabus": "Course overview", "schedule": "Monday"},
    s.PolicySerializer: {
        "id": 1,
        "workspace_id": 1,
        "version": 1,
        "effective_from": AT,
        "can_ta_post_announcements": False,
        "decision_version": "A9-LMS-BP-0.2",
        "author_user_id": 1,
    },
    s.PolicyInput: {"can_ta_post_announcements": True},
    s.SectionSerializer: {
        "id": 1,
        "workspace_id": 1,
        "kind": "WEEK",
        "label": "Week 1",
        "order": 0,
    },
    s.SectionInput: {"kind": "WEEK", "label": "Week 1", "order": 0},
    s.MaterialSerializer: MATERIAL,
    s.MaterialInput: {"kind": "NOTE", "text": "Read chapter one", "title": "Lesson"},
    s.AssignmentSerializer: ASSIGNMENT,
    s.AssignmentInput: {
        key: ASSIGNMENT[key]
        for key in ("title", "instructions", "due_at", "submission_type", "points_possible")
    },
    s.AnnouncementSerializer: {
        "id": 1,
        "workspace_id": 1,
        "content": "Class starts Monday",
        "author_user_id": 1,
        "created_at": AT,
    },
    s.AnnouncementInput: {"content": "Class starts Monday"},
    s.SubmissionSerializer: SUBMISSION,
    s.SubmissionInput: {"kind": "TEXT", "text": "My answer"},
    s.GradeSerializer: GRADE,
    s.GradeInput: {"points": "15.00", "feedback": "Explain your reasoning"},
    s.ReleaseInput: {"release_at": "2026-12-01T09:00:00Z"},
    s.EmptyInput: {},
}


def examples_for(request, response, status=200):
    examples = []
    if request is not None:
        examples.append(OpenApiExample("Request", value=VALUES[request], request_only=True))
    if response in VALUES:
        value = dict(VALUES[response])
        if request is s.ReleaseInput:
            value.update(state="SCHEDULED", release_at=VALUES[s.ReleaseInput]["release_at"])
        if request is s.EmptyInput and response is s.GradeSerializer:
            value.update(state="RELEASED", released_at=AT, released_by_user_id=1)
        examples.append(
            OpenApiExample("Response", value=value, response_only=True, status_codes=[str(status)])
        )
    return examples
