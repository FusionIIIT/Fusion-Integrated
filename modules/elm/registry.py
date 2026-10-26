from fusion_inventory.modules.registry import ModuleRegistry, NavItem, NavGroup, Permission, PermissionLevel

MODULE = ModuleRegistry(
    name='ELM',
    label='Employee Leave Management',
    icon='<i class="fas fa-calendar-check"></i>',
    description='Manage employee leave balances and apply for leaves.',
    version='1.0.0',
    author='Your Name',
    author_email='your.email@example.com',
    url='http://www.yourwebsite.com',
    app_name='elm'
)

NAV_ITEMS = [
    NavItem(
        label='Leave Types',
        name='leave_type_list',
        url='elm:leave_type_list',
        icon='<i class="fas fa-list"></i>',
        group=NavGroup.CONFIGURATION,
        permissions=[
            Permission('view_leavetype', PermissionLevel.VIEW),
            Permission('add_leavetype', PermissionLevel.ADD),
            Permission('change_leavetype', PermissionLevel.CHANGE),
            Permission('delete_leavetype', PermissionLevel.DELETE),
        ]
    ),
    NavItem(
        label='Leave Balances',
        name='leave_balance_list',
        url='elm:leave_balance_list',
        icon='<i class="fas fa-user-clock"></i>',
        group=NavGroup.TRANSACTIONS,
        permissions=[
            Permission('view_leavebalance', PermissionLevel.VIEW),
            Permission('add_leavebalance', PermissionLevel.ADD),
            Permission('change_leavebalance', PermissionLevel.CHANGE),
            Permission('delete_leavebalance', PermissionLevel.DELETE),
        ]
    ),
    NavItem(
        label='Leave Applications',
        name='leave_application_list',
        url='elm:leave_application_list',
        icon='<i class="fas fa-file-alt"></i>',
        group=NavGroup.TRANSACTIONS,
        permissions=[
            Permission('view_leaveapplication', PermissionLevel.VIEW),
            Permission('add_leaveapplication', PermissionLevel.ADD),
            Permission('change_leaveapplication', PermissionLevel.CHANGE),
            Permission('delete_leaveapplication', PermissionLevel.DELETE),
        ]
    ),
]