"""Pure validation for complaint submissions."""


class InvalidSubmission(ValueError):
    pass


def validate_submission(*, category: str, description: str) -> tuple[str, str]:
    clean_category = (category or "").strip()
    clean_description = (description or "").strip()
    if not clean_category:
        raise InvalidSubmission("Complaint category is required.")
    if not clean_description:
        raise InvalidSubmission("Complaint description is required.")
    return clean_category, clean_description
