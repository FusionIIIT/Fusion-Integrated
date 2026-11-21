from django.urls import path

from .views import (
    FileArchiveView,
    FileCreateView,
    FileDiscardView,
    FileEditView,
    FileForwardView,
    FileReturnView,
)

app_name = 'fts'

urlpatterns = [
    path('', FileCreateView.as_view(), name='file-create'),
    # Distinct paths to avoid Django's first-match URL routing collision
    path('<uuid:file_id>/edit/', FileEditView.as_view(), name='file-edit'),
    path('<uuid:file_id>/discard/', FileDiscardView.as_view(), name='file-discard'),
    path('<uuid:file_id>/forward/', FileForwardView.as_view(), name='file-forward'),
    path('<uuid:file_id>/return/', FileReturnView.as_view(), name='file-return'),
    path('<uuid:file_id>/archive/', FileArchiveView.as_view(), name='file-archive'),
]
