"""URL routing for MMS module."""
from django.urls import path

from modules.mms.api.views import (
    AnnouncementListView,
    BillListView,
    DeregistrationListView,
    FeedbackListView,
    MenuListView,
    RebateListView,
    RegistrationListView,
    SpecialFoodListView,
)

urlpatterns = [
    path("menu/", MenuListView.as_view(), name="mms-menu-list"),
    path("announcements/", AnnouncementListView.as_view(), name="mms-announcement-list"),
    path("registrations/", RegistrationListView.as_view(), name="mms-registration-list"),
    path("deregistrations/", DeregistrationListView.as_view(), name="mms-deregistration-list"),
    path("rebates/", RebateListView.as_view(), name="mms-rebate-list"),
    path("special-food/", SpecialFoodListView.as_view(), name="mms-special-food-list"),
    path("bills/", BillListView.as_view(), name="mms-bill-list"),
    path("feedback/", FeedbackListView.as_view(), name="mms-feedback-list"),
]
