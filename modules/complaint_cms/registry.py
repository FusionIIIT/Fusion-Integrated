MODULE = {
    'code': 'complaint_cms',
    'label': 'Complaint Management System',
    'base_path': '/complaints',
    'nav_section': 'Services',
    'icon': 'WarningCircle',
    'status': 'active',
    'sort_order': 40,
}

NAV_ITEMS = [
    {'code': 'complaint_cms.mine', 'label': 'My Complaints', 'icon': 'WarningCircle', 'to': '/complaints/mine', 'required_permission': 'complaint_cms.complaint.view_self', 'sort_order': 10},
    {'code': 'complaint_cms.queue', 'label': 'Complaint Queue', 'icon': 'ListChecks', 'to': '/complaints/queue', 'required_permission': 'complaint_cms.task.view', 'sort_order': 20},
    {'code': 'complaint_cms.admin', 'label': 'Complaint Admin', 'icon': 'Gear', 'to': '/complaints/admin', 'required_permission': 'complaint_cms.configuration.manage', 'sort_order': 30},
]

PERMISSIONS = (
    ('complaint_cms.complaint.view_self', 'View own complaints'),
    ('complaint_cms.complaint.create', 'Create new complaints'),
    ('complaint_cms.complaint.review', 'Review complaints'),
    ('complaint_cms.complaint.resolve', 'Resolve complaints'),
    ('complaint_cms.complaint.escalate', 'Escalate complaints'),
    ('complaint_cms.task.view', 'View task queue'),
    ('complaint_cms.configuration.manage', 'Manage configuration settings'),
    ('complaint_cms.record.manage', 'Manage record management'),
)

ROLE_GRANTS = {
    'student/faculty/staff': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create'],
    'Caretaker/Warden/Unit Incharge/Section Head': ['complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate', 'complaint_cms.task.view'],
    'Complaint Authority': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create', 'complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate', 'complaint_cms.task.view'],
    'Dean/Registrar/Director': ['complaint_cms.configuration.manage', 'complaint_cms.record.manage'],
}

SYSTEM_PERMISSIONS = []