from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import LeaveApplication

@login_required
def apply_leave(request):
    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        leave_type = request.POST.get("leave_type")
        reason = request.POST.get("reason", "").strip()

        if not all([start_date, end_date, leave_type]):
            messages.error(request, "Please fill in all required fields.")
        else:
            try:
                from datetime import date
                start = date.fromisoformat(start_date)
                end = date.fromisoformat(end_date)
                if start < timezone.localdate() or end < start:
                    raise ValueError
                if leave_type not in dict(LeaveApplication.LEAVE_TYPES):
                    raise ValueError
                LeaveApplication.objects.create(
                    user=request.user,
                    start_date=start,
                    end_date=end,
                    leave_type=leave_type,
                    reason=reason,
                )
                messages.success(request, "Leave application submitted.")
                return redirect("leave_management:apply_leave")
            except ValueError:
                messages.error(request, "Please check the dates and leave type.")

    applications = LeaveApplication.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "leave_management/apply_leave.html", {
        "applications": applications,
        "leave_types": LeaveApplication.LEAVE_TYPES,
    })
