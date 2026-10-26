"""API views for Employee Leave Management."""

from datetime import date
from uuid import UUID

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.elm.models import LeaveApplication
from modules.elm.services.applications import (
    LeaveApplicationError,
    decide_leave,
    submit_leave,
    transition_leave,
)
from modules.elm.services.authz import require


def serialize_application(application):
    """Convert a leave application to a JSON-compatible dictionary."""
    return {
        "id": str(application.id),
        "employee_id": application.employee_id,
        "leave_type": application.leave_type,
        "start_date": application.start_date.isoformat(),
        "end_date": application.end_date.isoformat(),
        "reason": application.reason,
        "start_half": application.start_half,
        "end_half": application.end_half,
        "requested_days": str(application.requested_days),
        "status": application.status,
        "approver_id": application.approver_id,
        "decision_note": application.decision_note,
        "submitted_at": (
            application.submitted_at.isoformat()
            if application.submitted_at
            else None
        ),
        "decided_at": (
            application.decided_at.isoformat()
            if application.decided_at
            else None
        ),
    }


def get_actor(request):
    """Return the authenticated principal supplied by the platform."""
    return getattr(request, "principal", None)


class MyLeaveApplicationsView(APIView):
    """List leave applications belonging to the current employee."""

    def get(self, request):
        actor = get_actor(request)
        require(actor, "elm.application.view_self")

        employee_id = str(getattr(actor, "id", ""))

        if not employee_id:
            return Response(
                {"detail": "Employee identity is unavailable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        applications = LeaveApplication.objects.filter(
            employee_id=employee_id
        )

        return Response(
            [serialize_application(item) for item in applications]
        )


class SubmitLeaveApplicationView(APIView):
    """Submit a leave application."""

    def post(self, request):
        actor = get_actor(request)
        require(actor, "elm.application.create")

        data = request.data

        try:
            start_date = date.fromisoformat(data.get("start_date", ""))
            end_date = date.fromisoformat(data.get("end_date", ""))

            application = submit_leave(
                employee_id=str(getattr(actor, "id", "")),
                leave_type=str(data.get("leave_type", "")),
                start_date=start_date,
                end_date=end_date,
                reason=str(data.get("reason", "")),
                start_half=str(data.get("start_half", "")),
                end_half=str(data.get("end_half", "")),
            )
        except (ValueError, TypeError, LeaveApplicationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            serialize_application(application),
            status=status.HTTP_201_CREATED,
        )


class DecideLeaveApplicationView(APIView):
    """Approve or reject a submitted leave application."""

    def post(self, request, application_id):
        actor = get_actor(request)
        require(actor, "elm.application.approve")

        try:
            UUID(str(application_id))
            application = LeaveApplication.objects.get(pk=application_id)
            approver_id = str(getattr(actor, "id", ""))
            if not approver_id:
                return Response(
                    {"detail": "Approver identity is unavailable."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if application.employee_id == approver_id:
                return Response(
                    {"detail": "You cannot approve or reject your own leave application."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            decision = request.data.get("decision", "")
            if decision not in ("approve", "reject"):
                return Response(
                    {"detail": "Decision must be 'approve' or 'reject'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application = decide_leave(
                application_id=application_id,
                approver_id=approver_id,
                approve=(decision == "approve"),
                decision_note=str(request.data.get("decision_note", "")),
            )
        except LeaveApplication.DoesNotExist:
            return Response(
                {"detail": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (ValueError, TypeError, LeaveApplicationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serialize_application(application))



class LeaveLifecycleView(APIView):
    """Withdraw, cancel, request an extension, or record resumption."""

    def post(self, request, application_id):
        actor = get_actor(request)
        action = request.data.get("action", "")
        permission_by_action = {
            "withdraw": "elm.application.withdraw",
            "cancel": "elm.application.cancel",
            "extend": "elm.application.extend",
            "resume": "elm.application.resume",
        }
        permission = permission_by_action.get(action)
        if permission is None:
            return Response(
                {"detail": "Action must be withdraw, cancel, extend, or resume."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        require(actor, permission)
        actor_id = str(getattr(actor, "id", ""))
        if not actor_id:
            return Response(
                {"detail": "Actor identity is unavailable."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            application = LeaveApplication.objects.get(pk=application_id)
            # Self-service lifecycle actions may only target the actor's own request.
            if application.employee_id != actor_id:
                return Response(
                    {"detail": "You may only change your own leave application."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            application = transition_leave(
                application_id=application_id,
                actor_id=actor_id,
                action=action,
                note=str(request.data.get("note", "")),
            )
        except LeaveApplication.DoesNotExist:
            return Response(
                {"detail": "Leave application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except LeaveApplicationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serialize_application(application))
