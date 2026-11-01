from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.department.models import Announcement
from modules.department.services.announcements import (
    create_draft,
    hide,
    publish,
    soft_delete,
)


def make_actor(
    permissions=None,
    user_id=101,
    active_role="Dept_Admin",
):
    permissions = permissions or set()

    def has_permission(code):
        return code in permissions

    return SimpleNamespace(
        user_id=user_id,
        active_role=active_role,
        has_permission=has_permission,
    )


class AnnouncementServiceTests(TestCase):
    def setUp(self):
        self.manager = make_actor(
            permissions={
                "department.announcement.view",
                "department.announcement.publish",
                "department.announcement.manage",
            },
            active_role="Dept_Admin",
        )

        self.hod = make_actor(
            permissions={
                "department.announcement.view",
                "department.announcement.publish",
                "department.announcement.manage",
            },
            user_id=202,
            active_role="HOD",
        )


    def test_non_hod_cannot_hide_announcement(self):
        announcement = self.create_draft_announcement()
        publish(
            announcement_id=announcement.pk,
            actor=self.manager,
            target_roles=["Student"],
            target_programs=["CSE"],
            target_academic_years=["2026"],
        )

        non_hod = make_actor(
            permissions={
                "department.announcement.publish",
                "department.announcement.manage",
            },
            active_role="Dept_Admin",
        )

        with self.assertRaises(PermissionDeniedError):
            hide(announcement_id=announcement.pk, actor=non_hod)

    def test_non_hod_cannot_delete_announcement(self):
        announcement = self.create_draft_announcement()

        non_hod = make_actor(
            permissions={
                "department.announcement.publish",
                "department.announcement.manage",
            },
            active_role="Dept_Admin",
        )

        with self.assertRaises(PermissionDeniedError):
            soft_delete(announcement_id=announcement.pk, actor=non_hod)

    def create_draft_announcement(self):
        return Announcement.objects.create(
            title="Department meeting",
            body="The meeting is scheduled for Monday.",
        )

    def test_create_draft_requires_publish_permission(self):
        actor = make_actor()

        with self.assertRaises(PermissionDeniedError):
            create_draft(
                actor=actor,
                title="Notice",
                body="Notice body",
            )

    def test_create_draft_trims_content(self):
        announcement = create_draft(
            actor=self.manager,
            title="  Notice  ",
            body="  Notice body  ",
        )

        self.assertEqual(announcement.title, "Notice")
        self.assertEqual(announcement.body, "Notice body")
        self.assertIsNone(announcement.published_at)

    def test_create_draft_rejects_empty_content(self):
        with self.assertRaises(ConflictError):
            create_draft(
                actor=self.manager,
                title="  ",
                body="Notice body",
            )

    def test_publish_records_actor_and_targets(self):
        announcement = self.create_draft_announcement()

        published = publish(
            announcement_id=announcement.pk,
            actor=self.manager,
            target_roles=["Student"],
            target_programs=["CSE"],
            target_academic_years=["2026"],
        )

        self.assertIsNotNone(published.published_at)
        self.assertEqual(published.published_by_user_id, 101)
        self.assertEqual(published.published_by_role, "Dept_Admin")
        self.assertEqual(published.target_roles, ["Student"])
        self.assertEqual(published.target_programs, ["CSE"])
        self.assertEqual(published.target_academic_years, ["2026"])

    def test_publish_rejects_empty_audience(self):
        announcement = self.create_draft_announcement()

        with self.assertRaises(ConflictError):
            publish(
                announcement_id=announcement.pk,
                actor=self.manager,
                target_roles=[],
                target_programs=["CSE"],
                target_academic_years=["2026"],
            )

    def test_publish_rejects_missing_announcement(self):
        with self.assertRaises(NotFoundError):
            publish(
                announcement_id=999999,
                actor=self.manager,
                target_roles=["Student"],
                target_programs=["CSE"],
                target_academic_years=["2026"],
            )

    def test_published_announcement_cannot_be_published_twice(self):
        announcement = self.create_draft_announcement()

        publish(
            announcement_id=announcement.pk,
            actor=self.manager,
            target_roles=["Student"],
            target_programs=["CSE"],
            target_academic_years=["2026"],
        )

        with self.assertRaises(ConflictError):
            publish(
                announcement_id=announcement.pk,
                actor=self.manager,
                target_roles=["Student"],
                target_programs=["CSE"],
                target_academic_years=["2026"],
            )

    def test_hide_removes_announcement_from_active_list(self):
        announcement = self.create_draft_announcement()

        publish(
            announcement_id=announcement.pk,
            actor=self.manager,
            target_roles=["Student"],
            target_programs=["CSE"],
            target_academic_years=["2026"],
        )

        hide(announcement_id=announcement.pk, actor=self.hod)

        announcement.refresh_from_db()
        self.assertTrue(announcement.is_hidden)
        self.assertFalse(announcement.is_active)

    def test_soft_delete_sets_deleted_timestamp(self):
        announcement = self.create_draft_announcement()

        deleted = soft_delete(
            announcement_id=announcement.pk,
            actor=self.hod,
        )

        self.assertIsNotNone(deleted.deleted_at)
        self.assertLessEqual(deleted.deleted_at, timezone.now())

    def test_hide_requires_permission(self):
        announcement = self.create_draft_announcement()

        with self.assertRaises(PermissionDeniedError):
            hide(
                announcement_id=announcement.pk,
                actor=make_actor(),
            )
