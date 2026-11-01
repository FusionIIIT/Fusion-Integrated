from django.conf import settings
from django.http import FileResponse
from django.urls import include, path, re_path
from django.views.static import serve

from devtools.psm_preview import PreviewLogin, PreviewMe


def app(request):
    return FileResponse(
        (settings.BASE_DIR / "client/dist/index.html").open("rb"), content_type="text/html"
    )


urlpatterns = [
    path("api/v1/me", PreviewMe.as_view()),
    path("api/v1/psm-preview/login", PreviewLogin.as_view()),
    path("api/v1/psm/", include("modules.psm.api.urls")),
    path("assets/<path:path>", serve, {"document_root": settings.BASE_DIR / "client/dist/assets"}),
    re_path(r"^(?!api/).*$", app),
]
