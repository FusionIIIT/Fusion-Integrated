"""Read-only course-association boundary; no academic registration writes."""

from collections.abc import Sequence

from django.conf import settings
from django.utils.module_loading import import_string

from core.api.exceptions import DomainError


class RegistrationUnavailable(DomainError):
    code = "registration_unavailable"
    status_code = 503


def get_course_contexts(user_ids: Sequence[int]) -> dict[int, list[dict]]:
    provider = getattr(settings, "LMS_COURSE_PROVIDER", "")
    if not provider:
        raise RegistrationUnavailable(
            "Configure the authoritative LMS course-registration provider."
        )
    try:
        result = _normalize(import_string(provider)(list(user_ids)), user_ids)
    except DomainError:
        raise
    except Exception as exc:
        raise RegistrationUnavailable(
            "The course-registration source could not confirm access."
        ) from exc
    else:
        return result


def _normalize(result, user_ids):
    if not isinstance(result, dict):
        raise TypeError("Expected a mapping keyed by IAM user ID.")
    output = {}
    for user_id in user_ids:
        rows = result.get(user_id, [])
        if not isinstance(rows, list):
            raise TypeError("Expected a list of course associations.")
        normalized = []
        for row in rows:
            if not isinstance(row, dict) or row.get("role") not in (
                "student",
                "faculty",
                "ta",
                "observer",
            ):
                raise ValueError("Invalid course role.")
            if type(row.get("course_id")) is not int or row["course_id"] < 1:
                raise ValueError("Invalid academic course ID.")
            if type(row.get("year")) is not int or not 1900 <= row["year"] <= 2200:
                raise ValueError("Invalid course year.")
            if row.get("semester_type") not in (
                "Odd Semester",
                "Even Semester",
                "Summer Semester",
            ):
                raise ValueError("Invalid course semester.")
            clean = {key: row[key] for key in ("course_id", "year", "semester_type", "role")}
            clean["code"] = str(row.get("code", row["course_id"]))[:40]
            clean["title"] = str(row.get("title", "Course"))[:200]
            clean["may_announce"] = row.get("may_announce") is True
            for key in ("instructors", "tas"):
                clean[key] = [
                    {
                        "user_id": item["user_id"],
                        "display_name": str(item.get("display_name", ""))[:200],
                    }
                    for item in row.get(key, [])
                    if isinstance(item, dict) and type(item.get("user_id")) is int
                ]
            normalized.append(clean)
        output[user_id] = normalized
    return output
