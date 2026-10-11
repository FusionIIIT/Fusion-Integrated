from django import forms
from fusionalm.models import Leave, LeaveRequest

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ('employee', 'leave_type', 'start_date', 'end_date')

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ('employee', 'leave_type', 'start_date', 'end_date')
