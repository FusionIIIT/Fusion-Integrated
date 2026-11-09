from django.core.mail import send_mail

def send_employee_added_email(employee_name, department_name):
    send_mail(
        'Employee Added',
        f'Employee {employee_name} has been added to department {department_name}.',
        'from@example.com',
        ['to@example.com'],
        fail_silently=True,
    )
