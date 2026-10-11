"""HR module URL routes."""
from django.urls import path

from modules.hr.api.views import (
    ContractCreateView,
    ContractEndView,
    ContractListView,
    DepartmentListView,
)

urlpatterns = [
    path("departments/", DepartmentListView.as_view(), name="hr-departments"),
    path("contracts/",   ContractListView.as_view(),   name="hr-contracts"),
    path("contracts/create/", ContractCreateView.as_view(), name="hr-contract-create"),
    path("contracts/<int:contract_id>/end/", ContractEndView.as_view(), name="hr-contract-end"),
]
