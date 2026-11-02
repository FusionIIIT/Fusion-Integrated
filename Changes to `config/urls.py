# config/urls.py
urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/v1/", include("fusion_auth.urls")),
    path("api/v1/directory/", include("modules.directory.api.urls")),
    path("api/v1/placement/", include("modules.placement.api.urls")),
    path("api/v1/leave/", include("modules.leave_elm.urls")),  # Add this line
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
