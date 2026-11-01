from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from core.api.exceptions import BadRequestError
from modules.complaints.services import _validate_attachments


class AttachmentValidationTests(SimpleTestCase):
    @override_settings(COMPLAINT_ATTACHMENT_CONTENT_TYPES=("application/pdf",),
                       COMPLAINT_ATTACHMENT_MAX_BYTES=100)
    def test_attachment_filename_is_sanitised(self):
        upload = SimpleUploadedFile("../../evidence.pdf", b"evidence",
                                    content_type="application/pdf")
        cleaned = _validate_attachments([upload])

        self.assertEqual(cleaned[0][1:], ("evidence.pdf", "application/pdf", 9))

    @override_settings(COMPLAINT_ATTACHMENT_CONTENT_TYPES=("application/pdf",),
                       COMPLAINT_ATTACHMENT_MAX_BYTES=5)
    def test_attachment_size_is_checked_before_storage(self):
        upload = SimpleUploadedFile("evidence.pdf", b"too large",
                                    content_type="application/pdf")
        with self.assertRaisesMessage(BadRequestError, "configured size limit"):
            _validate_attachments([upload])
