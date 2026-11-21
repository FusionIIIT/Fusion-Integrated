from django.test import TestCase
from django.core.exceptions import ValidationError, PermissionDenied
from modules.directory.models import UserRef
from modules.fts.models import FTSFile, FileMovement, FileAttachment, FileAuditLog
from modules.fts.services.file_service import (
    create_file, edit_draft, discard_draft, send_file, return_file,
    archive_file, get_inbox, get_outbox, get_drafts, get_archived
)

class TestFTSServices(TestCase):
    def setUp(self):
        self.user_a = UserRef.objects.create(user_id=101, username='faculty_a', email='a@iitdm.ac.in')
        self.user_b = UserRef.objects.create(user_id=102, username='hod_b', email='b@iitdm.ac.in')
        self.user_c = UserRef.objects.create(user_id=103, username='dean_c', email='c@iitdm.ac.in')

    def test_create_file(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        self.assertEqual(file.owner, self.user_a)
        self.assertEqual(file.status, 'draft')
        self.assertEqual(FileMovement.objects.filter(file=file, action='created').first().comments, "Valid comment")

    def test_create_file_missing_comment_raises(self):
        with self.assertRaises(ValidationError):
            create_file(owner=self.user_a, subject="Subject", initial_comment="")

    def test_edit_draft(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        edit_draft(file=file, user=self.user_a, subject="Updated")
        self.assertEqual(file.subject, "Updated")

    def test_edit_draft_non_owner_raises(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        with self.assertRaises(PermissionDenied):
            edit_draft(file=file, user=self.user_b, subject="Updated")

    def test_discard_draft(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        discard_draft(file=file, user=self.user_a)
        self.assertEqual(file.status, 'discarded')

    def test_send_file(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        movement = send_file(file=file, sender=self.user_a, receiver=self.user_b, comment="Forwarding")
        self.assertEqual(file.status, 'circulated')
        self.assertEqual(file.current_holder, self.user_b)
        self.assertEqual(movement.action, 'forwarded')

    def test_send_file_missing_comment_raises(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        with self.assertRaises(ValidationError):
            send_file(file=file, sender=self.user_a, receiver=self.user_b, comment="")

    def test_return_file(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        send_file(file=file, sender=self.user_a, receiver=self.user_b, comment="Forwarding")
        return_movement = return_file(file=file, sender=self.user_b, comment="Returning")
        self.assertEqual(file.current_holder, self.user_a)
        self.assertEqual(return_movement.action, 'returned')

    def test_archive_file(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        send_file(file=file, sender=self.user_a, receiver=self.user_b, comment="Forwarding")
        archive_file(file=file, user=self.user_a, comment="Archiving")
        self.assertEqual(file.status, 'archived')
        self.assertTrue(file.is_archived)

    def test_archive_by_non_owner_raises(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        send_file(file=file, sender=self.user_a, receiver=self.user_b, comment="Forwarding")
        with self.assertRaises(PermissionDenied):
            archive_file(file=file, user=self.user_b)

    def test_get_inbox_and_outbox(self):
        file = create_file(owner=self.user_a, subject="Subject", initial_comment="Valid comment")
        send_file(file=file, sender=self.user_a, receiver=self.user_b, comment="Forwarding")
        self.assertIn(file, get_inbox(user=self.user_b))
        self.assertIn(file, get_outbox(user=self.user_a))