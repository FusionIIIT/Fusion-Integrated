                                                                                      
from django.shortcuts import get_object_or_404                                        
from rest_framework import viewsets, status                                           
from rest_framework.response import Response                                          
from .models import LeaveApplication                                                  
                                                                                      
class LeaveApplicationViewSet(viewsets.ModelViewSet):                                 
    queryset = LeaveApplication.objects.all()                                         
    serializer_class = LeaveApplicationSerializer                                     
                                                                                      
    def approve_leave(self, request, pk):                                             
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted', 'recommended']:              
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        leave_application.status = 'approved'                                         
        leave_application.save()                                                      
        return Response(serializer.data)                                              
                                                                                      
    def reject_leave(self, request, pk):                                              
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted', 'recommended']:              
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        leave_application.status = 'rejected'                                         
        leave_application.save()                                                      
        return Response(serializer.data)                                              
                                                                                      
    def recommend_leave(self, request, pk):                                           
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted']:                             
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        leave_application.status = 'recommended'                                      
        leave_application.save()                                                      
        return Response(serializer.data)                                              
                                                                                      
    def finalize_leave(self, request, pk):                                            
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['recommended']:                           
            return Response({'error': 'Invalid status'},                              
        status=status.HTTP_400_BAD_REQUEST)                                                   
        leave_application.status = 'finalized'                                        
        leave_application.save()                                                      
        return Response(serializer.data)                                              

    def withdraw_leave(self, request, pk):                                            
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted']:                             
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        leave_application.status = 'withdrawn'                                        
        leave_application.save()                                                      
        return Response(serializer.data)                                              
                                                                                      
    def cancel_approved_leave(self, request, pk):                                     
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['approved']:                              
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        # Logic for restoring balance and finalizing cancellation                     
        return Response(serializer.data) 
    def select_substitute(self, request, pk):                                         
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted']:                             
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        # Logic for selecting a substitute employee                                   
        return Response(serializer.data)                                              
                                                                                      
    def record_substitute_consent(self, request, pk):                                 
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted']:                             
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        # Logic for recording substitute consent or decline                           
        return Response(serializer.data)                                              
                                                                                      
    def replace_declined_substitute(self, request, pk):                               
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted']:                             
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        # Logic for replacing a declined substitute                                   
        return Response(serializer.data)                                              
                                                                                      
    def withdraw_substitute_request(self, request, pk):                               
        leave_application = get_object_or_404(LeaveApplication, pk=pk)                
        if leave_application.status not in ['submitted']:                             
            return Response({'error': 'Invalid status'},                              
status=status.HTTP_400_BAD_REQUEST)                                                   
        # Logic for withdrawing the substitute request                                
        return Response(serializer.data) 


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):                             
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer 