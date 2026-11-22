from rest_framework.exceptions import APIException


class DependencyUnavailable(APIException):
    status_code = 503
    default_detail = "A required Fusion integration is unavailable."
    default_code = "integration_unavailable"
