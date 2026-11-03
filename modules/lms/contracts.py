from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

@dataclass(frozen=True)
class CourseDTO:
    id: int
    code: str
    title: str
    description: str
    syllabus: str
    schedule: str
    academic_year: int
    semester: int
    is_active: bool

@dataclass(frozen=True)
class CourseMembershipDTO:
    id: int
    course_id: int
    user_id: int
    role: str
    is_active: bool

@dataclass(frozen=True)
class AssignmentDTO:
    id: int
    course_id: int
    author_user_id: int
    title: str
    points_possible: int
    due_date: Any
    status: str

@dataclass(frozen=True)
class SubmissionDTO:
    id: int
    assignment_id: int
    student_user_id: int
    version: int
    submission_type: str
    status: str
    submitted_at: Any

@dataclass(frozen=True)
class GradeDTO:
    id: int
    submission_id: int
    assessor_user_id: int
    assessor_role: str
    points_awarded: int | None
    status: str
    released_at: Any

def get_courses(course_ids: Sequence[int]) -> Dict[int, CourseDTO]:
    from .models import Course
    return {course.id: CourseDTO(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        syllabus=course.syllabus,
        schedule=course.schedule,
        academic_year=course.academic_year,
        semester=course.semester,
        is_active=course.is_active
    ) for course in Course.objects.filter(id__in=course_ids)}

def get_user_courses(user_id: int) -> List[CourseDTO]:
    from .models import Course, CourseMembership
    memberships = CourseMembership.objects.filter(user_id=user_id)
    return [CourseDTO(
        id=membership.course.id,
        code=membership.course.code,
        title=membership.course.title,
        description=membership.course.description,
        syllabus=membership.course.syllabus,
        schedule=membership.course.schedule,
        academic_year=membership.course.academic_year,
        semester=membership.course.semester,
        is_active=membership.course.is_active
    ) for membership in memberships]

def get_course_memberships(course_id: int) -> List[CourseMembershipDTO]:
    from .models import CourseMembership
    return [CourseMembershipDTO(
        id=membership.id,
        course_id=membership.course.id,
        user_id=membership.user_id,
        role=membership.role,
        is_active=membership.is_active
    ) for membership in CourseMembership.objects.filter(course_id=course_id)]

def get_assignments(assignment_ids: Sequence[int]) -> Dict[int, AssignmentDTO]:
    from .models import Assignment
    return {assignment.id: AssignmentDTO(
        id=assignment.id,
        course_id=assignment.course.id,
        author_user_id=assignment.author_user_id,
        title=assignment.title,
        points_possible=assignment.points_possible,
        due_date=assignment.due_date,
        status=assignment.status
    ) for assignment in Assignment.objects.filter(id__in=assignment_ids)}
