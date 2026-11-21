from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from datetime import timedelta
from .models import (
    RegistrationRequest, DeregistrationRequest, MenuItem, 
    RebateRequest, SpecialFoodRequest, VacationSurvey, 
    VacationSurveyResponse, MonthlyBill, Feedback, Announcement
)

# --- Student Operations ---
class RegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        req = RegistrationRequest.objects.create(
            student=request.user,
            window_id=request.data.get('window_id')
        )
        return Response({"id": req.id, "status": req.status}, status=status.HTTP_201_CREATED)

class DeregistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        req = DeregistrationRequest.objects.create(student=request.user)
        return Response({"id": req.id, "status": req.status}, status=status.HTTP_201_CREATED)

class RebateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        rebate = RebateRequest.objects.create(
            student=request.user,
            reason=request.data.get('reason'),
            explanation=request.data.get('explanation', ''),
            start_date=request.data.get('start_date'),
            end_date=request.data.get('end_date')
        )
        return Response({"id": rebate.id, "status": rebate.status}, status=status.HTTP_201_CREATED)

class SpecialFoodView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        timeout = timezone.now() + timedelta(hours=12)
        sf = SpecialFoodRequest.objects.create(
            student=request.user,
            reason=request.data.get('reason'),
            requested_date=request.data.get('requested_date'),
            timeout_at=timeout
        )
        return Response({"id": sf.id, "status": sf.status}, status=status.HTTP_201_CREATED)

class VacationSurveyResponseView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, survey_id):
        resp, _ = VacationSurveyResponse.objects.update_or_create(
            survey_id=survey_id,
            student=request.user,
            defaults={'response': request.data.get('response', 'no').lower()}
        )
        return Response({"status": "recorded", "response": resp.response})

class FeedbackView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response(list(Feedback.objects.values()))
    def post(self, request):
        fb = Feedback.objects.create(student=request.user, content=request.data.get('content'))
        return Response({"id": fb.id, "status": "submitted"}, status=status.HTTP_201_CREATED)

class StudentBillView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        bills = MonthlyBill.objects.filter(student=request.user, status='published').values()
        return Response(list(bills))

# --- Caretaker & Administrative Management ---
class CaretakerReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, module_type, pk):
        decision = request.data.get('decision')  # 'approve' or 'reject'
        
        if module_type == 'registration':
            req = RegistrationRequest.objects.get(id=pk)
            req.status = 'approved' if decision == 'approve' else 'rejected'
            req.save()
            return Response({"status": req.status})
        
        elif module_type == 'deregistration':
            req = DeregistrationRequest.objects.get(id=pk)
            if decision == 'approve':
                req.status = 'approved_awaiting'
                req.effective_date = timezone.now().date() + timedelta(days=1)
            else:
                req.status = 'rejected'
            req.save()
            return Response({"status": req.status, "effective_date": req.effective_date})
            
        elif module_type == 'rebate':
            rebate = RebateRequest.objects.get(id=pk)
            rebate.status = 'approved' if decision == 'approve' else 'rejected'
            if decision == 'approve' and request.data.get('approved_start_date'):
                rebate.approved_start_date = request.data.get('approved_start_date')
                rebate.approved_end_date = request.data.get('approved_end_date')
            rebate.save()
            return Response({"status": rebate.status})

        elif module_type == 'special-food':
            sf = SpecialFoodRequest.objects.get(id=pk)
            if decision in ['served', 'cancelled']:
                sf.status = decision
            else:
                sf.status = 'approved' if decision == 'approve' else 'rejected'
            sf.save()
            return Response({"status": sf.status})

        return Response({"error": "Invalid request type"}, status=status.HTTP_400_BAD_REQUEST)

class BillingManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, bill_id=None):
        action = request.data.get('action')
        if action == 'generate':
            # Generate dummy bills for registered students
            month = request.data.get('month', 11)
            year = request.data.get('year', 2026)
            bill, _ = MonthlyBill.objects.update_or_create(
                student=request.user, month=month, year=year,
                defaults={'status': 'generated', 'total_amount': 3600.0}
            )
            return Response({"message": "Bill generated", "id": bill.id})
        elif action == 'publish' and bill_id:
            bill = MonthlyBill.objects.get(id=bill_id)
            bill.status = 'published'
            bill.published_at = timezone.now()
            bill.save()
            return Response({"status": "published"})
        return Response({"error": "Invalid billing action"}, status=status.HTTP_400_BAD_REQUEST)

class AnnouncementView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response(list(Announcement.objects.values()))
    def post(self, request):
        ann = Announcement.objects.create(
            author=request.user,
            title=request.data.get('title'),
            content=request.data.get('content')
        )
        return Response({"id": ann.id, "status": "published"}, status=status.HTTP_201_CREATED)

class MenuView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response(list(MenuItem.objects.values()))
    def post(self, request):
        item, _ = MenuItem.objects.update_or_create(
            day=request.data.get('day'),
            meal=request.data.get('meal'),
            defaults={'items': request.data.get('items')}
        )
        return Response({"status": "updated"})

# --- Supervisory Oversight & Reports (Warden / Caretaker) ---
class ReportsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, report_type):
        if report_type == 'registrations':
            return Response(list(RegistrationRequest.objects.values()))
        elif report_type == 'rebates':
            return Response(list(RebateRequest.objects.values()))
        elif report_type == 'special-meals':
            return Response(list(SpecialFoodRequest.objects.values()))
        elif report_type == 'vacation-summary':
            return Response(list(VacationSurveyResponse.objects.values()))
        return Response({"error": "Unknown report type"}, status=status.HTTP_400_BAD_REQUEST)