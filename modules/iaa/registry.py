"""IAA module navigation and permission grants consumed by permission_manifest."""
MODULE={"code":"iaa","label":"Internal Audit & Accounts","icon":"FileSearch","base_path":"/iaa","nav_section":"Administration","sort_order":40,"status":"active"}
NAV_ITEMS=[
{"code":"iaa.requests","label":"Expense / Voucher Requests","icon":"Receipt","to":"/iaa/requests","required_permission":"iaa.request.view_self","sort_order":10},
{"code":"iaa.ta","label":"Travel Allowance","icon":"Plane","to":"/iaa/ta","required_permission":"iaa.ta.view_self","sort_order":20},
{"code":"iaa.finance","label":"Finance Review","icon":"ClipboardCheck","to":"/iaa/finance","required_permission":"iaa.finance.validate","sort_order":30},
{"code":"iaa.approvals","label":"Approval Queue","icon":"Stamp","to":"/iaa/approvals","required_permission":"iaa.approval.decide","sort_order":40},
{"code":"iaa.anomalies","label":"Anomalies","icon":"AlertTriangle","to":"/iaa/anomalies","required_permission":"iaa.anomaly.view","sort_order":50},
{"code":"iaa.observations","label":"Audit Observations","icon":"ShieldCheck","to":"/iaa/observations","required_permission":"iaa.audit.review","sort_order":60},
{"code":"iaa.reports","label":"Reports & Dashboards","icon":"ChartBar","to":"/iaa/reports","required_permission":"iaa.report.view","sort_order":70},
{"code":"iaa.notifications","label":"Notifications","icon":"Bell","to":"/iaa/notifications","required_permission":"iaa.notification.view","sort_order":80},
{"code":"iaa.configuration","label":"IAA Configuration","icon":"Settings","to":"/iaa/configuration","required_permission":"iaa.configuration.manage","sort_order":90}]
PERMISSIONS=[
("iaa.request.create","Create expense/voucher drafts"),("iaa.request.view_self","View own financial requests"),
("iaa.request.view","View permitted operational financial requests"),("iaa.request.submit","Submit financial requests"),
("iaa.query.respond","Respond to Finance clarification"),("iaa.finance.query","Raise Finance clarification"),
("iaa.finance.validate","Review and validate expense/voucher requests"),("iaa.finance.record","Internally record completed requests"),
("iaa.ta.create","Create TA claims"),("iaa.ta.view_self","View own TA claims"),("iaa.ta.submit","Submit TA claims"),
("iaa.ta.verify","Verify TA claims"),("iaa.approval.view","View assigned approval decisions"),("iaa.approval.decide","Approve or reject routed requests"),
("iaa.anomaly.view","View anomalies in permitted scope"),("iaa.anomaly.flag","Flag material anomalies"),("iaa.anomaly.resolve","Resolve or escalate assigned anomalies"),
("iaa.audit.review","Review financial records and audit observations"),("iaa.observation.create","Raise audit observations"),
("iaa.observation.respond","Respond to audit observations"),("iaa.observation.verify","Verify and close audit observations"),
("iaa.report.view","View role-scoped reports"),("iaa.report.export","Export role-scoped reports"),
("iaa.notification.view","View personal IAA notifications"),("iaa.configuration.manage","Manage IAA configuration"),
("iaa.approval.escalate","System escalation of overdue approvals"),("iaa.anomaly.auto_create","System creation of rule-triggered anomalies")]
SYSTEM_PERMISSIONS=["iaa.approval.escalate","iaa.anomaly.auto_create"]
BASIC=["iaa.request.create","iaa.request.view_self","iaa.request.submit","iaa.query.respond","iaa.ta.create","iaa.ta.view_self","iaa.ta.submit","iaa.observation.respond","iaa.notification.view","iaa.anomaly.view"]
FINANCE=["iaa.request.view","iaa.finance.query","iaa.finance.validate","iaa.finance.record","iaa.ta.verify","iaa.anomaly.view","iaa.anomaly.flag","iaa.anomaly.resolve","iaa.report.view","iaa.report.export","iaa.notification.view"]
AUTHORITY=["iaa.request.view","iaa.approval.view","iaa.approval.decide","iaa.anomaly.view","iaa.anomaly.resolve","iaa.report.view","iaa.report.export","iaa.notification.view"]
AUDITOR=["iaa.request.view","iaa.anomaly.view","iaa.anomaly.flag","iaa.anomaly.resolve","iaa.audit.review","iaa.observation.create","iaa.observation.verify","iaa.report.view","iaa.report.export","iaa.notification.view"]
ROLE_GRANTS={"Basic User":BASIC,"basic_user":BASIC,"employee":BASIC,"faculty":BASIC,"staff":BASIC,"department_representative":BASIC,
"Finance Staff":FINANCE,"finance_staff":FINANCE,"HoD":AUTHORITY,"hod":AUTHORITY,"Head of Department":AUTHORITY,
"Dean":AUTHORITY,"dean":AUTHORITY,"Director":AUTHORITY,"director":AUTHORITY,
"Auditor":AUDITOR,"auditor":AUDITOR,"System Admin":["iaa.configuration.manage"],"system_admin":["iaa.configuration.manage"]}
