"""Institute Accounts and Audits (IAA) Module Registry (ADR-0010)."""

MODULE = {
    "code": "iaa",
    "label": "Accounts & Audits",
    "icon": "CurrencyInr",
    "base_path": "/iaa",
    "nav_section": "Finance",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "iaa.workspace",
        "label": "IAA Workspace",
        "icon": "Receipt",
        "to": "/iaa",
        "required_permission": "iaa.expense.view",
        "sort_order": 10,
    },
    {
        "code": "iaa.expenses",
        "label": "Expense Requests",
        "icon": "FileText",
        "to": "/iaa/expenses",
        "required_permission": "iaa.expense.view",
        "sort_order": 20,
    },
    {
        "code": "iaa.ta",
        "label": "TA Claims",
        "icon": "AirplaneTilt",
        "to": "/iaa/ta",
        "required_permission": "iaa.ta.view",
        "sort_order": 30,
    },
    {
        "code": "iaa.budgets",
        "label": "Department Budgets",
        "icon": "Bank",
        "to": "/iaa/budgets",
        "required_permission": "iaa.budget.view",
        "sort_order": 40,
    },
    {
        "code": "iaa.anomalies",
        "label": "Anomalies",
        "icon": "WarningCircle",
        "to": "/iaa/anomalies",
        "required_permission": "iaa.anomaly.view",
        "sort_order": 50,
    },
    {
        "code": "iaa.audit",
        "label": "Audit Observations",
        "icon": "ShieldCheck",
        "to": "/iaa/audit",
        "required_permission": "iaa.audit.view",
        "sort_order": 60,
    },
]
