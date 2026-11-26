from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.timetable_serializers import (
    DeptLabSerializer,
    DeptProgramSerializer,
    DeptSlotUploadSerializer,
    DeptSlotWriteSerializer,
    DeptTimetableSlotSerializer,
)
from modules.department.models import AcademicProgram, LabResource, TimetableSlot
from modules.department.selectors import resources as resource_selectors
from modules.department.services import resources as resource_service


@extend_schema(
    summary="List and create timetable slots",
    responses={
        200: DeptTimetableSlotSerializer,
        201: DeptTimetableSlotSerializer,
        400: None,
        403: None,
    },
    tags=["Timetable"],
)
class TimetableListView(ListCreateAPIView):
    """Lists and creates timetable slots."""
    serializer_class = DeptTimetableSlotSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.timetable.view"),
    ]
    queryset = TimetableSlot.objects.none()

    def get_queryset(self) -> QuerySet[TimetableSlot]:
        """Returns the queryset of visible timetable slots."""
        if getattr(self, "swagger_fake_view", False):
            return TimetableSlot.objects.none()
        return resource_selectors.visible_slots(self.request.principal)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeptSlotUploadSerializer
        return DeptTimetableSlotSerializer

    def create(self, request, *args, **kwargs):
        """Creates new timetable slots via upload."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        slots = resource_service.upload_slots(
            actor=request.principal,
            department_id=data["department"],
            slots=data['slots']
        )
        return Response([DeptTimetableSlotSerializer(slot).data for slot in slots], status=201)


@extend_schema(
    summary="Update a specific timetable slot",
    responses={
        200: DeptTimetableSlotSerializer,
        204: None,
        400: None,
        403: None,
    },
    tags=["Timetable"],
)
class TimetableDetailView(APIView):
    """Updates or deletes a specific timetable slot."""
    serializer_class = DeptTimetableSlotSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.timetable.update"),
    ]
    queryset = TimetableSlot.objects.none()

    def get_object(self, pk):
        return self.queryset.filter(id=pk).first()

    def patch(self, request, pk):
        """Partially updates a timetable slot."""
        slot = self.get_object(pk)
        serializer = DeptSlotWriteSerializer(instance=slot, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_slot = resource_service.update_slot(
            actor=request.principal,
            slot_id=pk,
            data=serializer.validated_data
        )
        return Response(DeptTimetableSlotSerializer(updated_slot).data)

    def delete(self, request, pk):
        """Deletes a timetable slot."""
        slot = self.get_object(pk)
        resource_service.delete_slot(actor=request.principal, slot_id=pk)
        return Response(status=204)


@extend_schema(
    summary="List available labs",
    responses={
        200: DeptLabSerializer,
        201: DeptLabSerializer,
        400: None,
        403: None,
    },
    tags=["Lab"],
)
class LabListView(ListCreateAPIView):
    """Lists and creates lab resources."""
    serializer_class = DeptLabSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.lab.view"),
    ]
    queryset = LabResource.objects.none()

    def get_queryset(self) -> QuerySet[LabResource]:
        """Returns the queryset of visible labs."""
        if getattr(self, "swagger_fake_view", False):
            return LabResource.objects.none()
        return resource_selectors.visible_labs(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new lab resource."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        lab = resource_service.save_lab(
            actor=request.principal,
            department_id=data.pop("department").id,
            name=data['name'],
            equipment=data.get('equipment'),
            capacity=data.get('capacity'),
            location=data.get('location'),
            notes=data.get('notes'),
        )
        return Response(DeptLabSerializer(lab).data, status=201)


@extend_schema(
    summary="Update a specific lab resource",
    responses={
        200: DeptLabSerializer,
        400: None,
        403: None,
    },
    tags=["Lab"],
)
class LabDetailView(APIView):
    """Updates a specific lab resource."""
    serializer_class = DeptLabSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.lab.update"),
    ]
    queryset = LabResource.objects.none()

    def get_object(self, pk):
        return self.queryset.filter(id=pk).first()

    def patch(self, request, pk):
        """Partially updates a lab resource."""
        lab = self.get_object(pk)
        serializer = DeptLabSerializer(instance=lab, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_lab = resource_service.save_lab(
            actor=request.principal,
            lab_id=pk,
            **serializer.validated_data
        )
        return Response(DeptLabSerializer(updated_lab).data)


@extend_schema(
    summary="List available academic programs",
    responses={
        200: DeptProgramSerializer,
        201: DeptProgramSerializer,
        400: None,
        403: None,
    },
    tags=["Program"],
)
class ProgramListView(ListCreateAPIView):
    """Lists and creates academic programs."""
    serializer_class = DeptProgramSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.program.view"),
    ]
    queryset = AcademicProgram.objects.none()

    def get_queryset(self) -> QuerySet[AcademicProgram]:
        """Returns the queryset of visible academic programs."""
        if getattr(self, "swagger_fake_view", False):
            return AcademicProgram.objects.none()
        return resource_selectors.visible_programs(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new academic program."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        program = resource_service.save_program(
            actor=request.principal,
            department_id=data.pop("department").id,
            name=data['name'],
            level=data.get('level'),
            description=data.get('description'),
        )
        return Response(DeptProgramSerializer(program).data, status=201)


@extend_schema(
    summary="Update a specific academic program",
    responses={
        200: DeptProgramSerializer,
        400: None,
        403: None,
    },
    tags=["Program"],
)
class ProgramDetailView(APIView):
    """Updates a specific academic program."""
    serializer_class = DeptProgramSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.program.update"),
    ]
    queryset = AcademicProgram.objects.none()

    def get_object(self, pk):
        return self.queryset.filter(id=pk).first()

    def patch(self, request, pk):
        """Partially updates an academic program."""
        program = self.get_object(pk)
        serializer = DeptProgramSerializer(instance=program, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_program = resource_service.save_program(
            actor=request.principal,
            program_id=pk,
            **serializer.validated_data
        )
        return Response(DeptProgramSerializer(updated_program).data)
