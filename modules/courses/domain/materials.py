"""Pure Python domain entities and validation rules for Course Materials (CFR-LMS-003)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from modules.courses.domain.errors import InvalidCourseDataError, UnauthorizedCourseActionError

ALLOWED_MATERIAL_TYPES = frozenset({"file", "link", "note"})


@dataclass(frozen=True)
class SectionCreateDTO:
    title: str
    description: str = ""
    sort_order: int = 0

    def validate(self) -> None:
        if not self.title or not self.title.strip():
            raise InvalidCourseDataError("Section title cannot be empty.")
        if len(self.title.strip()) > 120:
            raise InvalidCourseDataError("Section title cannot exceed 120 characters.")


@dataclass(frozen=True)
class SectionUpdateDTO:
    title: str | None = None
    description: str | None = None
    sort_order: int | None = None

    def validate(self) -> None:
        if self.title is not None:
            if not self.title.strip():
                raise InvalidCourseDataError("Section title cannot be empty.")
            if len(self.title.strip()) > 120:
                raise InvalidCourseDataError("Section title cannot exceed 120 characters.")


@dataclass(frozen=True)
class MaterialCreateDTO:
    title: str
    material_type: str
    description: str = ""
    link_url: str = ""
    content: str = ""
    has_file: bool = False
    is_published: bool = True
    release_at: datetime | None = None
    sort_order: int = 0

    def validate(self) -> None:
        if not self.title or not self.title.strip():
            raise InvalidCourseDataError("Material title cannot be empty.")
        if len(self.title.strip()) > 200:
            raise InvalidCourseDataError("Material title cannot exceed 200 characters.")

        if self.material_type not in ALLOWED_MATERIAL_TYPES:
            raise InvalidCourseDataError(
                f"Invalid material type {self.material_type!r}. Must be one of: {sorted(ALLOWED_MATERIAL_TYPES)}"
            )

        if self.material_type == "link":
            if not self.link_url or not self.link_url.strip():
                raise InvalidCourseDataError("External link URL is required for link material.")
            parsed = urlparse(self.link_url.strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise InvalidCourseDataError("External link must be a valid http or https URL.")

        elif self.material_type == "file":
            if not self.has_file and not self.link_url:
                raise InvalidCourseDataError("A file upload is required for file material.")

        elif self.material_type == "note":
            if not self.content.strip() and not self.description.strip():
                raise InvalidCourseDataError("Note content or description is required for note material.")


@dataclass(frozen=True)
class MaterialUpdateDTO:
    title: str | None = None
    description: str | None = None
    link_url: str | None = None
    content: str | None = None
    section_id: int | None = None
    clear_section: bool = False
    is_published: bool | None = None
    release_at: datetime | None = None
    clear_release_at: bool = False
    sort_order: int | None = None

    def validate(self) -> None:
        if self.title is not None:
            if not self.title.strip():
                raise InvalidCourseDataError("Material title cannot be empty.")
            if len(self.title.strip()) > 200:
                raise InvalidCourseDataError("Material title cannot exceed 200 characters.")

        if self.link_url is not None and self.link_url.strip():
            parsed = urlparse(self.link_url.strip())
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise InvalidCourseDataError("External link must be a valid http or https URL.")


def validate_material_author(role: str | None) -> None:
    """Enforce that only assigned faculty instructors can author/edit materials (BR-LMS-004)."""
    if role != "instructor":
        raise UnauthorizedCourseActionError(
            "Only assigned faculty instructors may create, edit, or delete course materials."
        )

