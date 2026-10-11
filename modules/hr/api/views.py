"""DRF API views for HR module."""
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hr.api.serializers import (
    CreateContractSerializer,
    DepartmentSerializer,
    EmploymentContractSerializer,
    EndContractSerializer,
)
from modules.hr.selectors import hr as selectors
from modules.hr.services import hr as services


class DepartmentListView(generics.ListCreateAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [HasModuleGrant("hr"), HasPermission("hr.department.view")]

    def get_queryset(self):
        return selectors.departments_all()

    @extend_schema(summary="List departments")
    def get(self, *a, **kw):
        return super().get(*a, **kw)

    @extend_schema(summary="Create department")
    def post(self, request, *a, **kw):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dept = services.create_department(
            name=ser.validated_data["name"],
            code=ser.validated_data["code"],
            parent_id=ser.validated_data.get("parent").id if ser.validated_data.get("parent") else None,
            head_user_id=ser.validated_data.get("head_user_id"),
            actor_user_id=request.principal.user_id,
        )
        return Response(DepartmentSerializer(dept).data, status=status.HTTP_201_CREATED)


class ContractListView(generics.ListAPIView):
    serializer_class = EmploymentContractSerializer
    permission_classes = [HasModuleGrant("hr"), HasPermission("hr.employee.view")]

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        if user_id:
            return selectors.contracts_for_user(int(user_id))
        return selectors.active_contracts_all()


class ContractCreateView(APIView):
    permission_classes = [HasModuleGrant("hr"), HasPermission("hr.employee.manage")]

    @extend_schema(request=CreateContractSerializer, responses={201: EmploymentContractSerializer})
    def post(self, request):
        ser = CreateContractSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        c = services.create_contract(
            user_id=ser.validated_data["user_id"],
            department_id=ser.validated_data["department_id"],
            title=ser.validated_data["title"],
            kind=ser.validated_data.get("kind", "permanent"),
            starts_on=ser.validated_data["starts_on"],
            ends_on=ser.validated_data.get("ends_on"),
            actor_user_id=request.principal.user_id,
        )
        return Response(EmploymentContractSerializer(c).data, status=status.HTTP_201_CREATED)


class ContractEndView(APIView):
    permission_classes = [HasModuleGrant("hr"), HasPermission("hr.employee.manage")]

    @extend_schema(request=EndContractSerializer, responses={200: EmploymentContractSerializer})
    def post(self, request, contract_id: int):
        ser = EndContractSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        c = services.end_contract(
            contract_id=contract_id,
            ends_on=ser.validated_data["ends_on"],
            reason=ser.validated_data.get("reason", ""),
            actor_user_id=request.principal.user_id,
        )
        return Response(EmploymentContractSerializer(c).data, status=status.HTTP_200_OK)
