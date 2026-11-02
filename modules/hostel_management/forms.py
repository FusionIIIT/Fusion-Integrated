from django import forms
from .models import StudentAllocation, LeaveRequest

class StudentAllocationForm(forms.ModelForm):
    class Meta:
        model = StudentAllocation
        fields = ['room']

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
