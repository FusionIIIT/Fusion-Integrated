from modules.mess.models import RegistrationRequest, DeregistrationRequest, RebateRequest
from django.db.models import Count, Q

def registered_students(search=None):
    if search:
        students = RegistrationRequest.objects.exclude(user_id__contains=search)
    else:
        students = RegistrationRequest.objects.all()
    return students.values_list('user_id', flat=True)

def rebate_summary(status=None):
    if status:
        rebates = RebateRequest.objects.filter(status=status)
    else:
        rebates = RebateRequest.objects.all()
    return rebates.values('status').annotate(count=Count('status'))

def vacation_summary(survey_id):
    yes_count = RebateRequest.objects.filter(Q(survey_id=survey_id) & Q(response='YES')).count()
    no_count = RebateRequest.objects.filter(Q(survey_id=survey_id) & Q(response='NO')).count()
    default_no_count = RebateRequest.objects.filter(Q(survey_id=survey_id) & Q(response='DEFAULT_NO')).count()
    return {'YES': yes_count, 'NO': no_count, 'DEFAULT_NO': default_no_count}
