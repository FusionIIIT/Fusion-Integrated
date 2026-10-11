from django.contrib import admin                                                      
from .models import LeaveApplication, LeaveBalance                                    
                                                                                      
@admin.register(LeaveApplication)                                                     
class LeaveApplicationAdmin(admin.ModelAdmin):                                        
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status',     
'created_at', 'updated_at')                                                           
    list_filter = ('employee', 'leave_type', 'status')                                
    search_fields = ('employee__username', 'leave_type')                              
    readonly_fields = ('created_at', 'updated_at')                                    
                                                                                      
@admin.register(LeaveBalance)                                                         
class LeaveBalanceAdmin(admin.ModelAdmin):                                            
    list_display = ('employee', 'leave_type', 'balance')                              
    list_filter = ('employee', 'leave_type')                                          
    search_fields = ('employee__username', 'leave_type') 