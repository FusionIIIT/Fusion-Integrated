import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from .models import (
    Course, CourseMembership, CourseMaterial, Assignment
)


@login_required
@require_GET
def course_list(request):
    memberships = CourseMembership.objects.filter(
        user=request.user
    ).select_related("course")

    courses = [
        {
            "id": item.course.id,
            "course_code": item.course.course_code,
            "course_name": item.course.course_name,
            "role": item.role,
        }
        for item in memberships
        if item.course.is_active
    ]

    return JsonResponse({"courses": courses})


@login_required
@require_GET
def course_materials(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    membership = get_object_or_404(
        CourseMembership,
        course=course,
        user=request.user
    )

    materials = CourseMaterial.objects.filter(
        course=course,
        is_published=True
    )

    if membership.role == "STUDENT":
        from django.utils import timezone
        materials = materials.filter(
            models.Q(release_at__isnull=True) |
            models.Q(release_at__lte=timezone.now())
        )

    data = [
        {
            "id": material.id,
            "title": material.title,
            "description": material.description,
            "type": material.material_type,
            "module": material.module_name,
        }
        for material in materials
    ]

    return JsonResponse({"materials": data})


@login_required
@require_GET
def course_assignments(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    get_object_or_404(
        CourseMembership,
        course=course,
        user=request.user
    )

    assignments = Assignment.objects.filter(
        course=course,
        is_published=True
    )

    from django.utils import timezone
    assignments = assignments.filter(
        models.Q(release_at__isnull=True) |
        models.Q(release_at__lte=timezone.now())
    )

    data = [
        {
            "id": assignment.id,
            "title": assignment.title,
            "instructions": assignment.instructions,
            "due_date": assignment.due_date.isoformat(),
            "total_points": assignment.total_points,
            "submission_type": assignment.submission_type,
        }
        for assignment in assignments
    ]

    return JsonResponse({"assignments": data})