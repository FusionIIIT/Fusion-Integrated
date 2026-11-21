from django.contrib import admin
from django.contrib.auth.models import User
from .models import LeaveType, LeaveBalance, LeaveRequest, LeaveWorkflowHistory


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'annual_quota', 'carry_forward', 
                    'requires_medical_evidence']
    search_fields = ['name']
    list_filter = ['carry_forward', 'requires_medical_evidence']
    
    fieldsets = (
        ('Leave Type Information', {
            'fields': ('name', 'description')
        }),
        ('Quota and Rules', {
            'fields': ('annual_quota', 'carry_forward', 
                       'requires_medical_evidence')
        }),
    )


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'leave_type', 'total_days', 
                    'consumed_days', 'pending_days']
    search_fields = ['user__username', 'leave_type__name']
    list_filter = ['leave_type__name']
    
    readonly_fields = ['total_days', 'consumed_days', 'pending_days']
    
    fieldsets = (
        ('User and Leave Type', {
            'fields': ('user', 'leave_type')
        }),
        ('Balance Information', {
            'fields': ('total_days', 'consumed_days', 'pending_days')
        }),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'leave_type', 'start_date', 'end_date', 
                    'status', 'created_at']
    search_fields = ['user__username', 'reason']
    list_filter = ['leave_type__name', 'status', 'station_leave']
    
    readonly_fields = ['user', 'leave_type', 'start_date', 'end_date', 
                       'total_days', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'leave_type', 'start_date', 'end_date', 
                       'total_days', 'reason')
        }),
        ('Contact and Station Leave', {
            'fields': ('station_leave', 'address_during_leave', 
                       'contact_during_leave', 'substitute_name')
        }),
        ('Status and Workflow', {
            'fields': ('status', 'remarks', 'created_at', 'updated_at')
        }),
    )


@admin.register(LeaveWorkflowHistory)
class LeaveWorkflowHistoryAdmin(admin.ModelAdmin):
    list_display = ['request', 'from_state', 'to_state', 
                    'action_taken', 'reviewer', 'timestamp']
    search_fields = ['request__user__username', 'remarks']
    list_filter = ['action_taken', 'timestamp']
    
    readonly_fields = ['request', 'from_state', 'to_state', 
                       'action_taken', 'timestamp']
    
    fieldsets = (
        ('Workflow Transition', {
            'fields': ('request', 'from_state', 'to_state')
        }),
        ('Action Details', {
            'fields': ('reviewer', 'action_taken', 'remarks')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
