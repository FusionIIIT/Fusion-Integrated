# entire file content 
from django.urls import path
from . import views

urlpatterns = [
    path('apply_leave/', views.apply_leave, name='apply_leave'),
    # ... rest of code
]
