from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from modules.department.models import Announcement


class AnnouncementModelTests(TestCase):
    def valid_announcement_data(self):
        return {
            "title": "Mid-semester examination notice",
            "body": "Mid-semester examinations begin next Monday.",
            "target_roles": ["Student"],
            "target_programs": ["CSE"],
            "target_academic_years": ["2026"],
        }

    def test_draft_announcement_can_be_created(self):
        announcement = Announcement.objects.create(
            title="Draft notice",
            body="This is a draft.",
        )

        self.assertIsNone(announcement.published_at)
        self.assertFalse(announcement.is_active)

    def test_published_announcement_requires_content_and_targets(self):
        announcement = Announcement(
            **self.valid_announcement_data(),
            published_at=timezone.now(),
        )

        announcement.full_clean()
        self.assertTrue(announcement.is_active)

    def test_published_announcement_requires_target_roles(self):
        data = self.valid_announcement_data()
        data["target_roles"] = []

        announcement = Announcement(**data, published_at=timezone.now())

        with self.assertRaises(ValidationError):
            announcement.full_clean()

    def test_published_announcement_requires_target_programs(self):
        data = self.valid_announcement_data()
        data["target_programs"] = []

        announcement = Announcement(**data, published_at=timezone.now())

        with self.assertRaises(ValidationError):
            announcement.full_clean()

    def test_published_announcement_requires_academic_years(self):
        data = self.valid_announcement_data()
        data["target_academic_years"] = []

        announcement = Announcement(**data, published_at=timezone.now())

        with self.assertRaises(ValidationError):
            announcement.full_clean()

    def test_hidden_announcement_is_not_active(self):
        announcement = Announcement.objects.create(
            **self.valid_announcement_data(),
            published_at=timezone.now(),
            is_hidden=True,
        )

        self.assertFalse(announcement.is_active)

    def test_deleted_announcement_is_not_active(self):
        announcement = Announcement.objects.create(
            **self.valid_announcement_data(),
            published_at=timezone.now(),
            deleted_at=timezone.now(),
        )

        self.assertFalse(announcement.is_active)

    def test_invalid_target_list_is_rejected(self):
        announcement = Announcement(
            **{
                **self.valid_announcement_data(),
                "target_roles": ["Student", 123],
            }
        )

        with self.assertRaises(ValidationError):
            announcement.full_clean()
