from django.urls import path
from .views import (
    AnnouncementListCreateView, InventoryItemListView,
    StockRequestCreateListView, StockRequestApprovalView,
    StockRequestIssueView, StockMovementLogListView,
)

urlpatterns = [
    path("announcements/", AnnouncementListCreateView.as_view(), name="department_announcements"),
    path("inventory/", InventoryItemListView.as_view(), name="department_inventory"),
    path("stock-requests/", StockRequestCreateListView.as_view(), name="department_stock_requests"),
    path("stock-requests/<int:pk>/decision/", StockRequestApprovalView.as_view(), name="department_stock_decision"),
    path("stock-requests/<int:pk>/issue/", StockRequestIssueView.as_view(), name="department_stock_issue"),
    path("movement-logs/", StockMovementLogListView.as_view(), name="department_movement_logs"),
]
