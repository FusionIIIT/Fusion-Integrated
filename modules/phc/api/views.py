from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.phc import services
from modules.phc.api.serializers import (
    PresenceSerializer,
    ScheduleSerializer,
    VisitCreateSerializer,
    VisitSerializer,
)
from modules.phc.models import DoctorSchedule, Visit

MODULE = HasModuleGrant("health_center")


class ScheduleListCreateView(generics.ListCreateAPIView):
    queryset = DoctorSchedule.objects.filter(published=True)
    serializer_class = ScheduleSerializer
    permission_classes = [MODULE]

    def get_permissions(self):
        code = (
            "health_center.schedule.manage"
            if self.request.method == "POST"
            else "health_center.schedule.view"
        )
        return [MODULE(), HasPermission(code)()]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return DoctorSchedule.objects.none()
        if principal.has_permission("health_center.schedule.manage"):
            return DoctorSchedule.objects.all()
        return DoctorSchedule.objects.filter(published=True)


class ScheduleDetailView(generics.UpdateAPIView):
    queryset = DoctorSchedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [MODULE, HasPermission("health_center.schedule.manage")]
    http_method_names = ["patch"]

    def get_permissions(self):
        return [super().get_permissions()[0], HasPermission("health_center.schedule.manage")()]


class SchedulePublishView(generics.GenericAPIView):
    queryset = DoctorSchedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = [MODULE, HasPermission("health_center.schedule.manage")]

    def post(self, request, *args, **kwargs):
        schedule = get_object_or_404(DoctorSchedule, pk=self.kwargs["pk"])
        services.publish_schedule(schedule)
        return Response(ScheduleSerializer(schedule).data, status=status.HTTP_200_OK)


class SchedulePresenceView(generics.GenericAPIView):
    queryset = DoctorSchedule.objects.all()
    serializer_class = PresenceSerializer
    permission_classes = [MODULE, HasPermission("health_center.schedule.manage")]

    def post(self, request, *args, **kwargs):
        schedule = get_object_or_404(DoctorSchedule, pk=self.kwargs["pk"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_presence(schedule, serializer.validated_data["is_present"])
        return Response(ScheduleSerializer(schedule).data, status=status.HTTP_200_OK)


class MyVisitListView(generics.ListAPIView):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    permission_classes = [MODULE, HasPermission("health_center.record.view_self")]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return Visit.objects.none()
        return (
            Visit.objects.filter(patient_id=principal.user_id).prefetch_related(
                "prescriptions"
            )
        )


class VisitListCreateView(generics.ListCreateAPIView):
    queryset = Visit.objects.all()
    serializer_class = VisitSerializer
    permission_classes = [MODULE, HasPermission("health_center.record.manage")]

    def get_queryset(self):
        patient_id = self.request.query_params.get("patient_id")
        if patient_id:
            return Visit.objects.filter(patient_id=int(patient_id))
        return Visit.objects.all()

    def create(self, request, *args, **kwargs):
        payload = VisitCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        prescriptions = data.pop("prescriptions")
        visit = services.record_visit(request.principal.user_id, prescriptions, **data)
        return Response(VisitSerializer(visit).data, status=status.HTTP_201_CREATED)
