from modules.hr_eis.models import Position


def get_position_by_id(position_id):
    return Position.objects.get(id=position_id)
