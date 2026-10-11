from django.urls import path, include                                                 
from .views import LeaveApplicationViewSet, LeaveBalanceViewSet                       
                                                                                      
urlpatterns = [                                                                       
    path('leave/', include(LeaveApplicationViewSet.router.urls)),                     
    path('leave-balance/', include(LeaveBalanceViewSet.router.urls)),                 
    path('leave/<int:pk>/approve/', LeaveApplicationViewSet.approve_leave),           
    path('leave/<int:pk>/reject/', LeaveApplicationViewSet.reject_leave),             
    path('leave/<int:pk>/recommend/', LeaveApplicationViewSet.recommend_leave),       
    path('leave/<int:pk>/finalize/', LeaveApplicationViewSet.finalize_leave),         
    path('leave/<int:pk>/withdraw/', LeaveApplicationViewSet.withdraw_leave),         
    path('leave/<int:pk>/cancel/', LeaveApplicationViewSet.cancel_approved_leave),    
    path('leave/<int:pk>/substitute/', LeaveApplicationViewSet.select_substitute),    
    path('leave/<int:pk>/substitute-consent/',                                        
LeaveApplicationViewSet.record_substitute_consent),                                   
    path('leave/<int:pk>/substitute-replace/',                                        
LeaveApplicationViewSet.replace_declined_substitute),                                 
    path('leave/<int:pk>/substitute-withdraw/',                                       
LeaveApplicationViewSet.withdraw_substitute_request),                                 
]                                                     