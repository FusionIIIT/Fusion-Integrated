from modules.hr_eis.services.position import get_position_by_id


def get_position_details(position_id):
    position = get_position_by_id(position_id)
    return {
        'id': position.id,
        'title': position.title,
        'ctc_lpa': position.ctc_lpa,
        'department': position.department.name,
    }
