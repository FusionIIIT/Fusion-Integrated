from rest_framework import status

from core.api.exceptions import DomainError


class IntegrationUnavailableError(DomainError):
    code = "integration_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "A required SPACS integration is not configured."
