import pytest
from django.db import IntegrityError
from django.utils import timezone
from modules.lms.domain.constants import ScheduleStatus
from modules.lms.models import Course, ModuleSection, CourseMaterial, Assignment, ScheduledRelease

pytestmark = pytest.mark.django_db


@pytest.fixture
def course():
    return Course.objects.create(code='CS101', title='Test Course', academic_year=2026, semester=1)


@pytest.fixture
def module_section(course):
    return ModuleSection.objects.create(course=course, title='Test Section')


@pytest.fixture
def material(module_section):
    return CourseMaterial.objects.create(section=module_section, title='Test Material')


@pytest.fixture
def assignment(course):
    return Assignment.objects.create(course=course, author_user_id=101, title='Test Assignment')


def test_scheduled_release_material_only_valid(material, assignment):
    release = ScheduledRelease.objects.create(
        material=material,
        assignment=None,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.PENDING,
    )
    assert release.id is not None
    assert release.material == material


def test_scheduled_release_assignment_only_valid(material, assignment):
    release = ScheduledRelease.objects.create(
        material=None,
        assignment=assignment,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.PENDING,
    )
    assert release.id is not None
    assert release.assignment == assignment


def test_scheduled_release_neither_target_raises_integrity_error(material, assignment):
    with pytest.raises(IntegrityError):
        ScheduledRelease.objects.create(
            material=None,
            assignment=None,
            scheduled_date=timezone.now(),
            status=ScheduleStatus.PENDING,
        )


def test_scheduled_release_both_targets_raises_integrity_error(material, assignment):
    with pytest.raises(IntegrityError):
        ScheduledRelease.objects.create(
            material=material,
            assignment=assignment,
            scheduled_date=timezone.now(),
            status=ScheduleStatus.PENDING,
        )


def test_scheduled_release_duplicate_active_material_raises_integrity_error(material, assignment):
    ScheduledRelease.objects.create(
        material=material,
        assignment=None,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.PENDING,
    )
    with pytest.raises(IntegrityError):
        ScheduledRelease.objects.create(
            material=material,
            assignment=None,
            scheduled_date=timezone.now(),
            status=ScheduleStatus.PROCESSING,
        )


def test_scheduled_release_duplicate_active_assignment_raises_integrity_error(material, assignment):
    ScheduledRelease.objects.create(
        material=None,
        assignment=assignment,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.PENDING,
    )
    with pytest.raises(IntegrityError):
        ScheduledRelease.objects.create(
            material=None,
            assignment=assignment,
            scheduled_date=timezone.now(),
            status=ScheduleStatus.PROCESSING,
        )


def test_scheduled_release_terminal_and_active_coexist(material, assignment):
    r1 = ScheduledRelease.objects.create(
        material=material,
        assignment=None,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.COMPLETED,
    )
    r2 = ScheduledRelease.objects.create(
        material=material,
        assignment=None,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.FAILED,
    )
    r3 = ScheduledRelease.objects.create(
        material=material,
        assignment=None,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.CANCELLED,
    )
    r4 = ScheduledRelease.objects.create(
        material=material,
        assignment=None,
        scheduled_date=timezone.now(),
        status=ScheduleStatus.PENDING,
    )
    assert ScheduledRelease.objects.filter(material=material).count() == 4
