from modules.mess.models import MenuItem, User
from modules.mess.services._audit import record_transition, queue_notification
from django.db.transaction import atomic

@atomic
def add_menu_item(actor_user_id, day_of_week, meal, item_name):
    if day_of_week < 0 or day_of_week > 6:
        raise ValueError("Invalid day_of_week. It should be 0 to 6.")
    if meal not in ['BREAKFAST', 'LUNCH', 'DINNER']:
        raise ValueError("Invalid meal. It should be BREAKFAST, LUNCH, or DINNER.")
    item = MenuItem(day_of_week=day_of_week, meal=meal, item_name=item_name)
    item.save()
    record_transition(actor_user_id, item.pk, 'ADDED')
    queue_notification('MENU_UPDATED', 0, {'day_of_week': day_of_week, 'meal': meal})
    return item

@atomic
def update_menu_item(actor_user_id, item_id, item_name):
    item = MenuItem.objects.get(pk=item_id)
    item.item_name = item_name
    item.updated_by = User.objects.get(pk=actor_user_id)
    item.save()
    record_transition(actor_user_id, item.pk, 'UPDATED')
    queue_notification('MENU_UPDATED', 0, {'day_of_week': item.day_of_week, 'meal': item.meal})
    return item

@atomic
def delete_menu_item(actor_user_id, item_id):
    item = MenuItem.objects.get(pk=item_id)
    item.deleted = True
    item.save()
    record_transition(actor_user_id, item.pk, 'DELETED')
    queue_notification('MENU_UPDATED', 0, {'day_of_week': item.day_of_week, 'meal': item.meal})
    return item
