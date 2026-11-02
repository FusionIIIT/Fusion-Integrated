from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import StudentAllocation, LeaveRequest
from .forms import StudentAllocationForm, LeaveRequestForm

@login_required
def dashboard_view(request):
    student_allocations = StudentAllocation.objects.filter(student=request.user, is_active=True)
    leave_requests = LeaveRequest.objects.filter(student=request.user)
    return render(request, 'hostel_management/dashboard.html', {
        'student_allocations': student_allocations,
        'leave_requests': leave_requests,
    })

@login_required
def allocate_room_view(request):
    if request.method == 'POST':
        form = StudentAllocationForm(request.POST)
        if form.is_valid():
            allocation = form.save(commit=False)
            allocation.student = request.user
            allocation.save()
            room = allocation.room
            room.vacant_beds -= 1
            room.save()
            return redirect('hostel_dashboard')
    else:
        form = StudentAllocationForm()
    return render(request, 'hostel_management/allocate_room.html', {'form': form})

@login_required
def leave_request_view(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            request_obj = form.save(commit=False)
            request_obj.student = request.user
            request_obj.status = 'Pending'
            request_obj.save()
            return redirect('hostel_dashboard')
    else:
        form = LeaveRequestForm()
    return render(request, 'hostel_management/leave_request.html', {'form': form})
