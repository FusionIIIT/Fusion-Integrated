from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from fusionalm.forms import LeaveForm, LeaveRequestForm
from fusionalm.models import Leave, LeaveRequest

@login_required
def leave_list(request):
    leaves = Leave.objects.filter(employee=request.user)
    return render(request, 'leave_list.html', {'leaves': leaves})

@login_required
def leave_request_list(request):
    leave_requests = LeaveRequest.objects.filter(employee=request.user)
    return render(request, 'leave_request_list.html', {'leave_requests': leave_requests})

@login_required
def create_leave(request):
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('leave_list')
    else:
        form = LeaveForm()
    return render(request, 'create_leave.html', {'form': form})

@login_required
def create_leave_request(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('leave_request_list')
    else:
        form = LeaveRequestForm()
    return render(request, 'create_leave_request.html', {'form': form})
