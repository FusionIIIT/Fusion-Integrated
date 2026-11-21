from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from fusion_auth.permissions import HasPermission

from modules.phc.models import PatientVisit, Prescription
from modules.phc.api.serializers import (
    PatientVisitSerializer,
    PrescriptionSerializer,
    PrescriptionCreateSerializer,
)
from modules.phc.services.patient import (
    record_visit,
    issue_prescription,
    export_medical_record_pdf,
)

class PatientVisitListCreateView(APIView):
    permission_classes = [HasPermission("phc.patient_visit.create")]

    @extend_schema(
        parameters=[OpenApiParameter("patient_user_id", int, OpenApiParameter.QUERY, required=False)],
        responses={200: PatientVisitSerializer(many=True)}
    )
    def get(self, request):
        patient_id = request.query_params.get("patient_user_id")
        visits = PatientVisit.objects.all()
        if patient_id:
            visits = visits.filter(patient_user_id=patient_id)
        return Response(PatientVisitSerializer(visits, many=True).data)

    @extend_schema(request=PatientVisitSerializer, responses={201: PatientVisitSerializer})
    def post(self, request):
        serializer = PatientVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = record_visit(
            patient_user_id=serializer.validated_data["patient_user_id"],
            visited_on=serializer.validated_data["visited_on"],
            notes=serializer.validated_data["notes"],
            recorded_by_user_id=request.user.user_id,
        )
        return Response(PatientVisitSerializer(visit).data, status=status.HTTP_201_CREATED)

class PrescriptionCreateView(APIView):
    permission_classes = [HasPermission("phc.prescription.create")]

    @extend_schema(
        parameters=[OpenApiParameter("pk", int, OpenApiParameter.PATH)],
        request=PrescriptionCreateSerializer,
        responses={201: PrescriptionSerializer}
    )
    def post(self, request, pk):
        serializer = PrescriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription = issue_prescription(
            visit_id=pk,
            details=serializer.validated_data["details"],
        )
        return Response(PrescriptionSerializer(prescription).data, status=status.HTTP_201_CREATED)

class MedicalRecordExportView(APIView):
    permission_classes = [HasPermission("phc.medical_record.export")]

    @extend_schema(
        parameters=[OpenApiParameter("patient_user_id", int, OpenApiParameter.QUERY, required=True)],
        responses={200: bytes}
    )
    def get(self, request):
        patient_id = int(request.query_params.get("patient_user_id", request.user.user_id))
        pdf_bytes = export_medical_record_pdf(patient_user_id=patient_id)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="medical_record_{patient_id}.pdf"'
        return response
