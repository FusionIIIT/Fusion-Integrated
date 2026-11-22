from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from modules.department import administration, selectors
from modules.department import permissions as p
from modules.department.api.common import DepartmentAccess
from modules.department.models import (
    DepartmentDetails,
    DepartmentProposal,
    LabResource,
    TimetableSlot,
)


class LabResourceSerializer(serializers.ModelSerializer):
    details = serializers.CharField(max_length=8000)

    class Meta:
        model = LabResource
        fields = ("id", "name", "details")


@method_decorator(never_cache, name="dispatch")
class LabResourcesView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_LABS
    write_permission = p.UPDATE_LABS
    queryset = LabResource.objects.none()
    serializer_class = LabResourceSerializer

    def get_queryset(self):
        return selectors.labs_for(self.request.principal)

    @extend_schema(responses=LabResourceSerializer)
    def post(self, request):
        payload = LabResourceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        lab = administration.save_lab(actor=request.principal, **payload.validated_data)
        return Response(LabResourceSerializer(lab).data)


class DepartmentTimetableSerializer(serializers.ModelSerializer):
    day = serializers.IntegerField(min_value=0, max_value=6)
    batch_year = serializers.IntegerField(min_value=1900, max_value=2200)
    instructor_id = serializers.IntegerField(min_value=1)

    class Meta:
        model = TimetableSlot
        fields = ("id", "term", "day", "starts_at", "ends_at", "programme", "batch_year",
                  "room", "instructor_id", "title", "kind")

    def validate(self, attrs):
        if attrs["ends_at"] <= attrs["starts_at"]:
            raise serializers.ValidationError({"ends_at": "End time must be after start time."})
        return attrs


class TimetableUploadSerializer(serializers.Serializer):
    slots = DepartmentTimetableSerializer(many=True, allow_empty=False, max_length=100)


@method_decorator(never_cache, name="dispatch")
class TimetableView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_TIMETABLE
    write_permission = p.UPDATE_TIMETABLE
    queryset = TimetableSlot.objects.none()
    serializer_class = DepartmentTimetableSerializer

    def get_queryset(self):
        return selectors.timetable_for(self.request.principal)

    @extend_schema(request=TimetableUploadSerializer,
                   responses={201: DepartmentTimetableSerializer(many=True)})
    def post(self, request):
        payload = TimetableUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        slots = administration.upload_timetable(actor=request.principal, **payload.validated_data)
        return Response(DepartmentTimetableSerializer(slots, many=True).data,
                        status=status.HTTP_201_CREATED)


class TimetableSlotView(DepartmentAccess, APIView):
    write_permission = p.UPDATE_TIMETABLE

    @extend_schema(request=DepartmentTimetableSerializer, responses=DepartmentTimetableSerializer)
    def put(self, request, pk):
        payload = DepartmentTimetableSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        slot = administration.replace_timetable_slot(actor=request.principal, slot_id=pk,
                                                     values=payload.validated_data)
        return Response(DepartmentTimetableSerializer(slot).data)


class AcademicContextSerializer(serializers.Serializer):
    programme = serializers.CharField(allow_blank=True)
    batch_year = serializers.IntegerField(allow_null=True)


@method_decorator(never_cache, name="dispatch")
class AcademicContextView(DepartmentAccess, APIView):
    read_permission = p.VIEW_TIMETABLE

    @extend_schema(responses=AcademicContextSerializer)
    def get(self, request):
        viewer = selectors.live_identity(request.principal)
        if not viewer or not selectors.department_for(request.principal, viewer):
            raise NotFoundError()
        return Response(AcademicContextSerializer(viewer).data)


class DepartmentDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentDetails
        fields = ("department", "official_name", "core_policies", "general_information")


class GeneralDetailsSerializer(serializers.Serializer):
    general_information = serializers.CharField(max_length=8000, allow_blank=True)


@method_decorator(never_cache, name="dispatch")
class DepartmentDetailsView(DepartmentAccess, APIView):
    read_permission = p.VIEW_DETAILS
    write_permission = p.UPDATE_DETAILS

    @extend_schema(responses=DepartmentDetailsSerializer)
    def get(self, request):
        row = selectors.details_for(request.principal)
        if row is None:
            raise NotFoundError()
        return Response(DepartmentDetailsSerializer(row).data)

    @extend_schema(request=GeneralDetailsSerializer, responses=DepartmentDetailsSerializer)
    def post(self, request):
        payload = GeneralDetailsSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = administration.update_general_details(
            actor=request.principal, **payload.validated_data,
        )
        return Response(DepartmentDetailsSerializer(row).data)


class DepartmentProposalSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = DepartmentProposal
        fields = ("id", "field", "value", "status", "decided_at")


class DepartmentProposalWriteSerializer(serializers.Serializer):
    field = serializers.ChoiceField(choices=DepartmentProposal.Field.choices)
    value = serializers.CharField(max_length=8000)

    def validate(self, attrs):
        if attrs["field"] == DepartmentProposal.Field.NAME and len(attrs["value"]) > 200:
            raise serializers.ValidationError({"value": "Enter at most 200 characters."})
        return attrs


@method_decorator(never_cache, name="dispatch")
class DepartmentProposalView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_DETAILS
    write_permission = p.PROPOSE_DETAILS
    queryset = DepartmentProposal.objects.none()
    serializer_class = DepartmentProposalSerializer

    def get_queryset(self):
        return selectors.proposals_for(self.request.principal)

    @extend_schema(request=DepartmentProposalWriteSerializer,
                   responses={201: DepartmentProposalSerializer})
    def post(self, request):
        payload = DepartmentProposalWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = administration.propose_official_details(
            actor=request.principal, **payload.validated_data,
        )
        return Response(DepartmentProposalSerializer(row).data, status=status.HTTP_201_CREATED)


class ProposalDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])


class ProposalDecisionView(DepartmentAccess, APIView):
    write_permission = p.APPROVE_DETAILS

    @extend_schema(request=ProposalDecisionSerializer, responses=DepartmentProposalSerializer)
    def post(self, request, pk):
        payload = ProposalDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = administration.decide_official_details(actor=request.principal, proposal_id=pk,
                                                     **payload.validated_data)
        return Response(DepartmentProposalSerializer(row).data)
