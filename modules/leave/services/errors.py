from core.api.exceptions import DomainError


class ValidationError(DomainError):
    """Invalid ELM business input, returned through Fusion's error envelope."""

    code = "validation_error"
    message = "The submitted data was not valid."
