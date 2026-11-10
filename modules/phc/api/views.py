from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from fusion_auth.permissions import HasPermission
from modules.phc.models import PatientVisit, Prescription
from modules.phc.api.serializers import PatientVisitSerializer, PrescriptionSerializer
from modules.phc.services.inventory import adjust_stock, create_requisition, decide_requisition, fulfill_requisition
from modules.phc.services.patients import record_patient_visit_and_prescription, generate_medical_record_pdf

class PatientVisitListView(APIView):
    permission_classes = [HasPermission("phc.patient_record.view")]

    @extend_schema(
        responses={200: PatientVisitSerializer(many=True)}
    )
    def get(self, request, user_id):
        qs = PatientVisit.objects.filter(patient_user_id=user_id).order_by("-visited_on")
        serializer = PatientVisitSerializer(qs, many=True)
        return Response(serializer.data)

class PatientVisitCreateView(APIView):
    permission_classes = [HasPermission("phc.patient_record.create")]

    @extend_schema(
        request=PatientVisitSerializer,
        responses={201: PatientVisitSerializer}
    )
    def post(self, request):
        serializer = PatientVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = serializer.save()
        return Response(serializer.data, status=201)

class PrescriptionListView(APIView):
    permission_classes = [HasPermission("phc.patient_record.view")]

    @extend_schema(
        responses={200: PrescriptionSerializer(many=True)}
    )
    def get(self, request, user_id):
        qs = Prescription.objects.filter(patient_visit__patient_user_id=user_id).order_by("-issued_on")
        serializer = PrescriptionSerializer(qs, many=True)
        return Response(serializer.data)

class MedicalRecordExportView(APIView):
    permission_classes = [HasPermission("phc.medical_record.export")]

    @extend_schema(
        responses={200: "application/pdf"}
    )
    def get(self, request):
        user_id = request.user.user_id
        try:
            pdf_bytes = generate_medical_record_pdf(user_id)
            response = Response(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f"attachment; filename=medical_records_{user_id}.pdf"
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=500)
