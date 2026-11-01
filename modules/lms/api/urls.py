from django.urls import path

from . import views

urlpatterns = [
    path("courses/", views.Courses.as_view()),
    path("courses/<int:pk>/", views.CourseDetail.as_view()),
    path("courses/<int:pk>/write/<str:kind>/", views.WriteContent.as_view()),
    path("courses/<int:pk>/write/<str:kind>/<int:item_id>/", views.UpdateContent.as_view()),
    path("courses/<int:pk>/assignments/<int:item_id>/publish/", views.Publish.as_view()),
    path("courses/<int:pk>/assignments/<int:item_id>/submit/", views.Submit.as_view()),
    path("courses/<int:pk>/submissions/<int:item_id>/grade/", views.Grade.as_view()),
    path("courses/<int:pk>/submissions/<int:item_id>/release/", views.Release.as_view()),
    path("courses/<int:pk>/download/<str:kind>/<int:item_id>/", views.Download.as_view()),
]
