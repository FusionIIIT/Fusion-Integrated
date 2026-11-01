from datetime import datetime
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import LeaveApplication, LeaveBalance

class ReviewLeaveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        decision = request.data.get("decision")
        remarks = request.data.get("remarks", "")
        user = request.user

        if decision not in ["approve", "reject", "recommend"]:
            return Response(
                {"error": "Invalid decision. Choose approve, reject, or recommend."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                leave = LeaveApplication.objects.select_for_update().get(pk=pk, status="AWAITING_UNIT_HEAD")

                if leave.applicant == user or not user.has_perm('can_approve'):
                    return Response(
                        {"error": "User is not authorized to review this leave application."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                if decision == "approve":
                    if leave.category in ["CL", "RH", "SCL", "EL", "COL", "VL"]:
                        duration = (leave.end_date - leave.start_date).days + 1

                        balance = LeaveBalance.objects.select_for_update().get(
                            user=leave.applicant,
                            year=datetime.now().year,
                        )

                        balance_fields = {
                            "CL": "casual_leave",
                            "RH": "restricted_holiday",
                            "SCL": "special_casual_leave",
                            "EL": "earned_leave",
                            "COL": "commuted_leave",
                            "VL": "vacation_leave",
                        }

                        field = balance_fields[leave.category]
                        available_balance = getattr(balance, field)

                        if available_balance < duration:
                            raise ValueError("Insufficient leave balance for approval.")

                        setattr(balance, field, available_balance - duration)
                        balance.save(update_fields=[field])

                    leave.status = "APPROVED"

                elif decision == "reject":
                    leave.status = "REJECTED"

                elif decision == "recommend":
                    remain_review = LeaveApplication.objects.filter(
                        applicant=leave.applicant,
                        status="AWAITING_REVIEW",
                    ).exists()

                    if remain_review:
                        leave.status = "AWAITING_MANAGER"
                    else:
                        leave.status = "AWAITING_FINAL"

                leave.remarks = remarks
                leave.save(update_fields=["status", "remarks"])

            return Response(
                {"message": f"Leave review updated to {leave.status}"},
                status=status.HTTP_200_OK,
            )

        except LeaveApplication.DoesNotExist:
            return Response(
                {"error": "Leave application not found or not awaiting unit head review."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except LeaveBalance.DoesNotExist:
            return Response(
                {"error": "Leave balance record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)