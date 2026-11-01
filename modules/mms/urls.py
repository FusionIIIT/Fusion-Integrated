from django.urls import path
from .views import RegistrationView, RebateView, SpecialFoodView, MenuView

urlpatterns = [
    path('register/', RegistrationView.as_view()),
    path('rebate/', RebateView.as_view()),
    path('special-food/', SpecialFoodView.as_view()),
    path('menu/', MenuView.as_view()),
]