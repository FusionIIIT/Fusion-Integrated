from django.urls import path
from . import views

app_name = 'fts'

urlpatterns = [
    path('inbox/', views.InboxView.as_view(), name='fts-inbox'),
    path('outbox/', views.OutboxView.as_view(), name='fts-outbox'),
    path('drafts/', views.DraftsView.as_view(), name='fts-drafts'),
    path('archived/', views.ArchivedView.as_view(), name='fts-archived'),
    path('files/', views.CreateFileView.as_view(), name='fts-create-file'),
    path('files/<int:pk>/', views.FileDetailView.as_view(), name='fts-file-detail'),
    path('files/<int:pk>/draft/', views.EditDraftView.as_view(), name='fts-edit-draft'),
    path('files/<int:pk>/discard/', views.DiscardDraftView.as_view(), name='fts-discard-draft'),
    path('files/<int:pk>/forward/', views.ForwardFileView.as_view(), name='fts-forward-file'),
    path('files/<int:pk>/return/', views.ReturnFileView.as_view(), name='fts-return-file'),
    path('files/<int:pk>/archive/', views.ArchiveFileView.as_view(), name='fts-archive-file'),
    path('files/<int:pk>/history/', views.FileHistoryView.as_view(), name='fts-file-history'),
    path('integration/files/', views.ConsumingModuleApiView.as_view(), name='fts-integration'),
]