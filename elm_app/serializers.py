                                                                                      
from rest_framework import serializers                                                
from .models import LeaveApplication, LeaveBalance                                    
                                                                                      
class LeaveApplicationSerializer(serializers.ModelSerializer):                        
    class Meta:                                                                       
        model = LeaveApplication                                                      
        fields = '__all__'                                                            
        validators = [                                                                
            serializers.ValidationError('Start date must be before end date.'),       
        ]                                                                             
                                                                                      
class LeaveBalanceSerializer(serializers.ModelSerializer):                            
    class Meta:                                                                       
        model = LeaveBalance                                                          
        fields = '__all__'       