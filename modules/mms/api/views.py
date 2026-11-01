from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from modules.mms import services
from modules.mms.models import RegistrationWindow, MenuItem, DayOfWeek, MealType

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated # Extend with institute student flag

class IsMessCaretaker(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.mms_roles.filter(role='caretaker', is_active=True).exists()

class ApplyRegistrationView(APIView):
    permission_classes = [IsStudent]
    def post(self, request):
        try:
            req = services.submit_registration(request.user, request.data.get('window_id'))
            return Response({"id": req.id, "status": req.status}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReviewRegistrationView(APIView):
    permission_classes = [IsMessCaretaker]
    def post(self, request, pk):
        try:
            req = services.review_registration(pk, request.data.get('decision'), request.data.get('remarks', ''))
            return Response({"id": req.id, "status": req.status})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SubmitRebateView(APIView):
    permission_classes = [IsStudent]
    def post(self, request):
        try:
            rebate = services.submit_rebate(
                student=request.user,
                reason=request.data.get('reason'),
                explanation=request.data.get('explanation', ''),
                start_date=request.data.get('start_date'),
                end_date=request.data.get('end_date')
            )
            return Response({"id": rebate.id, "status": rebate.status}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class WeeklyMenuView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        menu = MenuItem.objects.all().values('day', 'meal', 'items')
        return Response(list(menu))

    def post(self, request):
        if not IsMessCaretaker().has_permission(request, self):
            return Response({"error": "Only Caretaker can edit menu."}, status=status.HTTP_403_FORBIDDEN)
        item, _ = MenuItem.objects.update_or_create(
            day=request.data.get('day'),
            meal=request.data.get('meal'),
            defaults={'items': request.data.get('items')}
        )
        return Response({"status": "updated", "day": item.day, "meal": item.meal})