from datetime import date, timedelta                                                  
                                                                                      
def calculate_leave_days(start_date, end_date, leave_type):                           
    if leave_type in ['CL', 'RH']:                                                    
        days = (end_date - start_date).days + 1                                       
        if days % 2 == 1 and leave_type == 'CL':                                      
            days -= 0.5                                                               
        return days                                                                   
    elif leave_type in ['EL', 'COL', 'VL']:                                           
        days = (end_date - start_date).days + 1                                       
        return days                                                                   
                                                                                      
def validate_leave_balance(employee, start_date, end_date, leave_type):               
    balance = employee.leavebalance_set.get(leave_type=leave_type).balance            
    days = calculate_leave_days(start_date, end_date, leave_type)                     
    if days > balance:                                                                
        raise ValueError('Insufficient leave balance.')                               
                                                         