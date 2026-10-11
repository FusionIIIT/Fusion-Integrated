from typing import Any

from modules.registry import ModuleManifest


def get_manifest() -> ModuleManifest:
    """Return the leave module manifest for sidebar registration."""
    
    return ModuleManifest(
        code='leave',
        basePath='/leave/',
        load=lambda: {
            'routes': [
                {
                    'path': '/dashboard',
                    'component': 'LeaveDashboard',
                    'name': 'Leave Dashboard',
                },
                {
                    'path': '/form',
                    'component': 'LeaveApplicationForm',
                    'name': 'Apply for Leave',
                },
            ],
        },
    )
