from django.views.generic import ListView, DetailView

from .models import LeaveRequest


class LeaveRequestListView(ListView):
    model = LeaveRequest
    template_name = 'elm/leave_request_list.html'
    context_object_name = 'leave_requests'


class LeaveRequestDetailView(DetailView):
    model = LeaveRequest
    template_name = 'elm/leave_request_detail.html'
    context_object_name = 'leave_request'