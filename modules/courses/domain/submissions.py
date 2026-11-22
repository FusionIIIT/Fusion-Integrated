"""Pure Python domain entities and validation rules for Course Submissions (UC-LMS-010, BR-LMS-012, BR-LMS-013, BR-LMS-014)."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from modules.courses.domain.errors import InvalidCourseDataError, UnauthorizedCourseActionError

MAX_SUBMISSION_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED_SUBMISSION_TYPES = frozenset({"file", "text", "link"})
DISALLOWED_EXTENSIONS = frozenset({
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".ps1",
    ".vbs",
    ".msi",
    ".dll",
    ".com",
    ".scr",
    ".pif",
    ".application",
    ".jar",
})


@dataclass(frozen=True)
class SubmissionCreateDTO:
    submission_type: str = "file"
    content: str = ""
    link_url: str = ""
    has_file: bool = False
    filename: str = ""
    file_size: int = 0

    def validate(self) -> None:
        if self.submission_type not in ALLOWED_SUBMISSION_TYPES:
            raise InvalidCourseDataError(
                f"Invalid submission type {self.submission_type!r}. Must be one of: {sorted(ALLOWED_SUBMISSION_TYPES)}"
            )

        if self.submission_type == "file":
            if not self.has_file:
                raise InvalidCourseDataError("A file upload is required for file submissions.")
            if self.file_size > MAX_SUBMISSION_FILE_SIZE:
                raise InvalidCourseDataError("File size exceeds 25 MB limit.")
            if self.filename:
                lower_name = self.filename.lower()
                for ext in DISALLOWED_EXTENSIONS:
                    if lower_name.endswith(ext):
                        raise InvalidCourseDataError(
                            f"Files with extension '{ext}' are not permitted for security reasons."
                        )

        elif self.submission_type == "link":
            if not self.link_url or not self.link_url.strip():
                raise InvalidCourseDataError("External link URL is required for link submissions.")
            parsed = urlparse(self.link_url.strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise InvalidCourseDataError("External link must be a valid http or https URL.")

        elif self.submission_type == "text":
            if not self.content or not self.content.strip():
                raise InvalidCourseDataError("Text content is required for text submissions.")


def validate_student_submitter(role: str | None) -> None:
    """Enforce that only enrolled students can submit assignment work (BR-LMS-004, UC-LMS-010)."""
    if role != "student":
        raise UnauthorizedCourseActionError(
            "Only enrolled students may submit assignment work."
        )


def validate_submission_viewer(role: str | None, *, is_owner: bool) -> None:
    """Enforce observer prohibition (BR-LMS-003) and student privacy (BR-LMS-014)."""
    if role == "observer":
        raise UnauthorizedCourseActionError(
            "Observers are not permitted to view student submissions (BR-LMS-003)."
        )
    if role == "student" and not is_owner:
        raise UnauthorizedCourseActionError(
            "Students may only access their own submissions (BR-LMS-014)."
        )
