from modules.mess.models import MenuItem, Announcement, Feedback

def weekly_menu():
    weekdays = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }

    menu = {}
    for i in range(7):
        day = weekdays[i]
        menu[day] = {
            'BREAKFAST': [],
            'LUNCH': [],
            'DINNER': []
        }

        items = MenuItem.objects.filter(day_of_week=i)
        for item in items:
            menu[day]['BREAKFAST'].append(item.breakfast)
            menu[day]['LUNCH'].append(item.lunch)
            menu[day]['DINNER'].append(item.dinner)

    return menu

def announcement_history(limit=50):
    return Announcement.objects.all().order_by('-created_at')[:limit]

def list_feedback(limit=50):
    return Feedback.objects.filter(role__in=['Caretaker', 'Warden']).order_by('-created_at')[:limit]
