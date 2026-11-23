"""API errors for integrations that are required but not yet available."""

from rest_framework.exceptions import APIException


class AcademicAuthorizationUnavailable(APIException):
    """Fail closed while no trusted course or roster provider is configured."""

    status_code = 503
    default_detail = "Academic authorization is unavailable."
    default_code = "academic_authorization_unavailable"
