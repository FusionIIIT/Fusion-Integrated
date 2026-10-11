from django.db import models                                                          
from django.contrib.auth.models import User                                           
                                                                                      
class LeaveApplication(models.Model):                                                 
    employee = models.ForeignKey(User, on_delete=models.CASCADE)                      
    leave_type = models.CharField(max_length=3)                                       
    start_date = models.DateField()                                                   
    end_date = models.DateField()                                                     
    status = models.CharField(max_length=20)                                          
    substitute = models.ForeignKey(User, related_name='substitute_for', null=True,    
blank=True, on_delete=models.SET_NULL)                                                
    approval_history = models.TextField(blank=True)                                   
    requested_days = models.FloatField()                                              
    created_at = models.DateTimeField(auto_now_add=True)                              
    updated_at = models.DateTimeField(auto_now=True)                                  
                                                                                      
class LeaveBalance(models.Model):                                                     
    employee = models.ForeignKey(User, on_delete=models.CASCADE)                      
    leave_type = models.CharField(max_length=3)                                       
    balance = models.FloatField()       