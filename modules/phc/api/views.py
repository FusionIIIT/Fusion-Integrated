from django.db import IntegrityError
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.phc.api import serializers as s
from modules.phc.models import Announcement, Appointment, Consultation, Doctor, Medicine, Patient
from modules.phc.selectors import phc
from modules.phc.services import phc as service

MODULE = HasModuleGrant("phc")


class PatientListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    serializer_class = s.PatientSerializer
    queryset = Patient.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        qs = phc.patients_for(self.request.principal)
        query = self.request.query_params.get("q", "").strip()
        if len(query) > 100:
            raise BadRequestError("Search text is too long.", code="invalid_filter")
        if query:
            if query.isdigit():
                qs = qs.filter(user_id=int(query)) | qs.filter(patient_number__icontains=query)
            else:
                qs = qs.filter(patient_number__icontains=query)
        return qs.order_by("patient_number")

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("phc.patient.register_self", "phc.patient.register")()]
        return [MODULE(), HasPermission("phc.patient.view", "phc.patient.view_self")()]

    @extend_schema(
        request=s.PatientCreateSerializer,
        responses={201: s.PatientSerializer},
        examples=[OpenApiExample("register patient", value={}, request_only=True)],
    )
    def create(self, request, *args, **kwargs):
        payload = s.PatientCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        user_id = payload.validated_data.get("user_id", request.principal.user_id)
        patient = service.register_patient(user_id=user_id, actor=request.principal)
        return Response(s.PatientSerializer(patient).data, status=201)


class DoctorListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("phc.appointment.book", "phc.appointment.manage")]
    serializer_class = s.DoctorSerializer
    queryset = Doctor.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return phc.doctors_for(self.request.principal)


class DoctorCreateView(APIView):
    permission_classes = [MODULE, HasPermission("phc.doctor.register")]

    @extend_schema(
        request=s.DoctorCreateSerializer,
        responses={201: s.DoctorSerializer},
        examples=[
            OpenApiExample(
                "new doctor",
                value={"user_id": 4102, "specialty": "General Medicine"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        payload = s.DoctorCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            doctor = service.create_doctor(**payload.validated_data)
        except IntegrityError as exc:
            raise ConflictError(
                "This user is already registered as a doctor.", code="doctor_exists"
            ) from exc
        return Response(s.DoctorSerializer(doctor).data, status=201)


class DoctorDetailView(APIView):
    permission_classes = [MODULE, HasPermission("phc.appointment.manage")]

    @extend_schema(
        request=s.DoctorUpdateSerializer,
        responses=s.DoctorSerializer,
        examples=[
            OpenApiExample("availability update", value={"is_available": False}, request_only=True)
        ],
    )
    def patch(self, request, pk):
        if phc.doctor_for(request.principal, pk) is None:
            raise NotFoundError("Doctor not found.", code="not_found")
        payload = s.DoctorUpdateSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        doctor = service.update_doctor(doctor_id=pk, changes=payload.validated_data)
        return Response(s.DoctorSerializer(doctor).data)


class ScheduleView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        if self.request.method == "GET":
            return [MODULE(), HasPermission("phc.appointment.book", "phc.appointment.manage")()]
        return [MODULE(), HasPermission("phc.appointment.manage")()]

    @extend_schema(responses=s.ScheduleSerializer(many=True))
    def get(self, request):
        doctor_id = request.query_params.get("doctor_id")
        if doctor_id and not doctor_id.isdigit():
            raise BadRequestError("doctor_id must be a number.", code="invalid_filter")
        rows = phc.schedules(doctor_id)
        return Response(s.ScheduleSerializer(rows, many=True).data)

    @extend_schema(
        request=s.ScheduleSerializer,
        responses={201: s.ScheduleSerializer},
        examples=[
            OpenApiExample(
                "weekly schedule",
                value={
                    "doctor": 1,
                    "weekday": 0,
                    "starts_at": "09:00:00",
                    "ends_at": "17:00:00",
                    "slot_minutes": 15,
                    "effective_from": "2026-12-01",
                    "effective_until": None,
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        payload = s.ScheduleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        data["doctor_id"] = data.pop("doctor").pk
        if phc.doctor_for(request.principal, data["doctor_id"]) is None:
            raise NotFoundError("Doctor not found.", code="not_found")
        return Response(s.ScheduleSerializer(service.set_schedule(**data)).data, status=201)


class AppointmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    serializer_class = s.AppointmentSerializer
    queryset = Appointment.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return phc.appointments_for(self.request.principal).order_by("-starts_at")

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("phc.appointment.book")()]
        return [MODULE(), HasPermission("phc.appointment.view_self", "phc.appointment.view")()]

    @extend_schema(
        request=s.AppointmentCreateSerializer,
        responses={201: s.AppointmentSerializer},
        examples=[
            OpenApiExample(
                "appointment request",
                value={
                    "doctor_id": 1,
                    "starts_at": "2026-12-01T10:00:00+05:30",
                    "reason": "Routine consultation",
                },
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        patient = phc.active_patient_for_user(request.principal.user_id)
        if patient is None:
            raise NotFoundError(
                "Register as a PHC patient before booking.", code="patient_required"
            )
        payload = s.AppointmentCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        appt = service.book_appointment(
            patient_id=patient.pk, actor_user_id=request.principal.user_id, **payload.validated_data
        )
        return Response(s.AppointmentSerializer(appt).data, status=201)


class AppointmentTransitionView(APIView):
    permission_classes = [MODULE]

    @extend_schema(
        request=s.AppointmentTransitionSerializer,
        responses=s.AppointmentSerializer,
        examples=[
            OpenApiExample("confirm appointment", value={"status": "confirmed"}, request_only=True)
        ],
    )
    def post(self, request, pk):
        appt = phc.appointments_for(request.principal).filter(pk=pk).first()
        if appt is None:
            raise NotFoundError("Appointment not found.", code="not_found")
        if (
            appt.patient.user_id != request.principal.user_id
            and not request.principal.has_permission("phc.appointment.manage")
        ):
            raise NotFoundError("Appointment not found.", code="not_found")
        if (
            request.principal.has_permission("phc.appointment.manage")
            and phc.doctor_for(request.principal, appt.doctor_id) is None
        ):
            raise NotFoundError("Appointment not found.", code="not_found")
        payload = s.AppointmentTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        target = payload.validated_data["status"]
        if target == "cancelled" and appt.patient.user_id == request.principal.user_id:
            if not request.principal.has_permission("phc.appointment.book"):
                raise NotFoundError("Appointment not found.", code="not_found")
        elif not request.principal.has_permission("phc.appointment.manage"):
            raise NotFoundError("Appointment not found.", code="not_found")
        changed = service.transition_appointment(
            appointment_id=pk, actor=request.principal, **payload.validated_data
        )
        return Response(s.AppointmentSerializer(changed).data)


class ConsultationListView(generics.ListAPIView):
    permission_classes = [
        MODULE,
        HasPermission("phc.consultation.view", "phc.appointment.view_self"),
    ]
    serializer_class = s.ConsultationSerializer
    queryset = Consultation.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return phc.consultations_for(self.request.principal).order_by("-created_at")


class ConsultationCreateView(APIView):
    permission_classes = [MODULE, HasPermission("phc.consultation.record")]

    @extend_schema(
        request=s.ConsultationCreateSerializer,
        responses={201: s.ConsultationSerializer},
        examples=[
            OpenApiExample(
                "record consultation",
                value={
                    "symptoms": "Cough",
                    "diagnosis": "Upper respiratory infection",
                    "observations": "No fever",
                    "treatment": "Rest and fluids",
                    "medicines": [],
                },
                request_only=True,
            )
        ],
    )
    def post(self, request, appointment_id):
        payload = s.ConsultationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        consult = service.record_consultation(
            appointment_id=appointment_id, actor=request.principal, **payload.validated_data
        )
        return Response(s.ConsultationSerializer(consult).data, status=201)


class MedicineListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    serializer_class = s.MedicineSerializer
    queryset = Medicine.objects.none()

    def get_queryset(self):
        return phc.medicines()

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("phc.inventory.manage")()]
        return [MODULE(), HasPermission("phc.inventory.view", "phc.inventory.manage")()]

    @extend_schema(
        request=s.MedicineSerializer,
        responses={201: s.MedicineSerializer},
        examples=[
            OpenApiExample(
                "new medicine",
                value={
                    "name": "Paracetamol",
                    "unit": "tablet",
                    "low_stock_threshold": 10,
                    "expires_on": "2027-12-31",
                },
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        payload = s.MedicineSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        medicine = service.add_medicine(values=payload.validated_data)
        return Response(s.MedicineSerializer(medicine).data, status=201)


class MedicineStockView(APIView):
    permission_classes = [MODULE, HasPermission("phc.inventory.manage")]

    @extend_schema(
        request=s.StockSerializer,
        responses=s.MedicineSerializer,
        examples=[
            OpenApiExample(
                "add stock", value={"quantity": 100, "action": "addition"}, request_only=True
            )
        ],
    )
    def post(self, request, pk):
        payload = s.StockSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        medicine = service.stock(medicine_id=pk, actor=request.principal, **payload.validated_data)
        return Response(s.MedicineSerializer(medicine).data)


class InventoryTransactionListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission("phc.inventory.view", "phc.inventory.manage")]
    serializer_class = s.InventoryTransactionSerializer

    def get_queryset(self):
        medicine_id = self.request.query_params.get("medicine_id")
        if medicine_id and not medicine_id.isdigit():
            raise BadRequestError("medicine_id must be a number.", code="invalid_filter")
        return phc.inventory_transactions(medicine_id)


class AnnouncementListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    serializer_class = s.AnnouncementSerializer
    queryset = Announcement.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        return phc.announcements(self.request.principal)

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("phc.announcement.publish")()]
        return [MODULE(), HasPermission("phc.announcement.view", "phc.announcement.publish")()]

    @extend_schema(
        request=s.AnnouncementWriteSerializer,
        responses={201: s.AnnouncementSerializer},
        examples=[
            OpenApiExample(
                "health center notice",
                value={"title": "Clinic hours", "body": "The clinic is open from 9 AM."},
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        payload = s.AnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        announcement = service.publish_announcement(
            actor=request.principal, **payload.validated_data
        )
        return Response(s.AnnouncementSerializer(announcement).data, status=201)
