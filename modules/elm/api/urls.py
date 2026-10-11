from django.urls import path

from modules.elm.api.views import LeaveCatalogView

urlpatterns = [path("catalog", LeaveCatalogView.as_view(), name="elm-catalog")]
