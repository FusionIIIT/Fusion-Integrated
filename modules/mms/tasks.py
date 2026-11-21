from django.utils import timezone
from .models import DeregistrationRequest, VacationSurvey, VacationSurveyResponse, SpecialFoodRequest, RegistrationRequest

def activate_next_day_deregistrations():
    """Event-triggered UC: MMS-UC-027"""
    today = timezone.now().date()
    DeregistrationRequest.objects.filter(
        status='approved_awaiting',
        effective_date__lte=today
    ).update(status='effective')

def apply_default_vacation_no():
    """Event-triggered UC: MMS-UC-028"""
    now = timezone.now()
    expired_surveys = VacationSurvey.objects.filter(deadline__lte=now, is_open=True)
    for survey in expired_surveys:
        responded_ids = VacationSurveyResponse.objects.filter(survey=survey).values_list('student_id', flat=True)
        registered_students = RegistrationRequest.objects.filter(status='approved').values_list('student_id', flat=True).distinct()
        
        missing_students = set(registered_students) - set(responded_ids)
        for student_id in missing_students:
            VacationSurveyResponse.objects.create(
                survey=survey,
                student_id=student_id,
                response='default_no'
            )
        survey.is_open = False
        survey.save()

def auto_reject_special_food_timeouts():
    """Event-triggered UC: MMS-UC-029"""
    SpecialFoodRequest.objects.filter(
        status='requested',
        timeout_at__lte=timezone.now()
    ).update(status='rejected')