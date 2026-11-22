"""Keep the multipart allowance scoped to the public identity upload route."""

from django.http import JsonResponse


class RequestBodyLimitMiddleware:
    REGISTRATION_PATH = "/api/v1/vms/registrations"
    WALK_IN_PATH = "/api/v1/vms/gate/walk-ins"
    DEFAULT_LIMIT = 1024 * 1024
    REGISTRATION_LIMIT = 6 * 1024 * 1024

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw_length = request.META.get("CONTENT_LENGTH")
        if raw_length:
            try:
                length = int(raw_length)
            except (TypeError, ValueError):
                return JsonResponse({"detail": "Invalid request size."}, status=400)
            is_registration = (
                request.path in {self.REGISTRATION_PATH, self.WALK_IN_PATH}
                and request.method == "POST"
            )
            is_event_guest_csv = (
                request.path.startswith("/api/v1/vms/admin/events/")
                and request.path.endswith("/guests")
                and request.method == "POST"
            )
            limit = (
                self.REGISTRATION_LIMIT
                if is_registration
                else 1024 * 1024
                if is_event_guest_csv
                else self.DEFAULT_LIMIT
            )
            if length < 0 or length > limit:
                return JsonResponse({"detail": "Request body exceeds the size limit."}, status=413)
        return self.get_response(request)
