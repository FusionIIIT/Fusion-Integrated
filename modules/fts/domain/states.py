from enum import Enum


class FileStatus(Enum):
    DRAFT = "DRAFT"
    CIRCULATED = "CIRCULATED"
    ARCHIVED = "ARCHIVED"
    DISCARDED = "DISCARDED"
