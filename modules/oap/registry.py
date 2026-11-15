MODULE = {
    'code': 'oap', 'label': 'Other Academic Procedures', 'icon': 'AcademicCap',
    'base_path': '/oap', 'nav_section': 'Academics', 'sort_order': 20,
    'status': 'active',
}

NAV_ITEMS = [
    {'code': 'oap.leave', 'label': 'Student Leave', 'icon': 'Calendar', 'to': '/oap/leave', 'required_permission': 'oap.leave.view', 'sort_order': 10},
    {'code': 'oap.bonafide', 'label': 'Bonafide Certificates', 'icon': 'FileText', 'to': '/oap/bonafide', 'required_permission': 'oap.bonafide.view', 'sort_order': 20},
    {'code': 'oap.nodues', 'label': 'No-Dues Clearance', 'icon': 'CheckCircle', 'to': '/oap/nodues', 'required_permission': 'oap.nodues.view', 'sort_order': 30},
    {'code': 'oap.assistantship', 'label': 'PG Assistantship', 'icon': 'CurrencyDollar', 'to': '/oap/assistantship', 'required_permission': 'oap.assistantship.view', 'sort_order': 40},
    {'code': 'oap.seminar', 'label': 'Graduate Seminars', 'icon': 'Users', 'to': '/oap/seminar', 'required_permission': 'oap.seminar.view', 'sort_order': 50},
]

ROLE_PERMISSIONS = {
    'student': ['oap.leave.view', 'oap.bonafide.view', 'oap.nodues.view'],
    'hod': ['oap.leave.view', 'oap.bonafide.view', 'oap.nodues.view', 'oap.assistantship.view', 'oap.seminar.view'],
    'faculty': ['oap.leave.view', 'oap.bonafide.view', 'oap.nodues.view', 'oap.assistantship.view', 'oap.seminar.view'],
    'academic_admin': ['oap.leave.view', 'oap.bonafide.view', 'oap.nodues.view', 'oap.assistantship.view', 'oap.seminar.view'],
    'department_admin': ['oap.leave.view', 'oap.bonafide.view', 'oap.nodues.view', 'oap.assistantship.view', 'oap.seminar.view'],
}