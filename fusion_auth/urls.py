from django.urls import path

from fusion_auth.views import LoginView, LogoutView, MeView

urlpatterns = [
    path("me", MeView.as_view(), name="me"),
    path("auth/login", LoginView.as_view(), name="login"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
]
