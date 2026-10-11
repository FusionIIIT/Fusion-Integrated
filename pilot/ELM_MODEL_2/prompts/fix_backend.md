Fix pass (backend). These are the errors reported by the repository's own checks after the previous steps. Fix them by editing the files shown. Do not delete functionality just to silence an error.

```
### manage.py check
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "manage.py", line 9, in <module>
    execute_from_command_line(sys.argv)
django.core.exceptions.ImproperlyConfigured: Cannot import 'leave'. Check that 'modules.leave.apps.LeaveConfig.name' is correct.
[exit 1]
### makemigrations --check
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "manage.py", line 9, in <module>
    execute_from_command_line(sys.argv)
django.core.exceptions.ImproperlyConfigured: Cannot import 'leave'. Check that 'modules.leave.apps.LeaveConfig.name' is correct.
[exit 1]
### ruff errors only (F, E9)
invalid-syntax: Expected a statement
 --> modules/leave/domain/__init__.py:1:1
  |
1 | // empty
  | ^^

F811 Redefinition of unused `get_el_from_vl_conversion` from line 64
  --> modules/leave/domain/policy.py:69:9
   |
67 |     # BR-EL-008 — Treatment of EL created by VL conversion
68 |     @staticmethod
69 |     def get_el_from_vl_conversion(principal: int, vl_days: int) -> int:
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^ `get_el_from_vl_conversion` redefined here
70 |         return vl_days // 2  # EL created by VL conversion
   |
  ::: modules/leave/domain/policy.py:64:9
   |
63 |     @staticmethod
64 |     def get_el_from_vl_conversion(principal: int, vl_days: int) -> int:
   |         ------------------------- previous definition of `get_el_from_vl_conversion` here
65 |         return vl_days // 2  # EL created by VL conversion
   |
help: Remove definition: `get_el_from_vl_conversion`

invalid-syntax: Only one '*' separator allowed
  --> modules/leave/services/applications.py:14:92
   |
13 | @transaction.atomic
14 | def apply_leave(principal_id: int, *, leave_category: str, start_date: str, end_date: str, *, reason: str = None, substitute_id: int =…
   |                                                                                            ^
15 |     """
16 |     Apply for leave.
   |

Found 3 errors.
[exit 1]
### nav items match client routes
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "ops/checks/nav_matches_routes.py", line 91, in <module>
    raise SystemExit(main())
  File "ops/checks/nav_matches_routes.py", line 37, in main
    django.setup()
django.core.exceptions.ImproperlyConfigured: Cannot import 'leave'. Check that 'modules.leave.apps.LeaveConfig.name' is correct.
[exit 1]
### permission manifest (make permissions)
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "manage.py", line 9, in <module>
    execute_from_command_line(sys.argv)
django.core.exceptions.ImproperlyConfigured: Cannot import 'leave'. Check that 'modules.leave.apps.LeaveConfig.name' is correct.
[exit 1]
### no cross-module foreign keys
Traceback (most recent call last):
  File "/opt/homebrew/Cellar/python@3.12/3.12.15/Frameworks/Python.framework/Versions/3.12/lib/python3.12/importlib/__init__.py", line 90, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "ops/checks/no_cross_module_fk.py", line 50, in <module>
    raise SystemExit(main())
  File "ops/checks/no_cross_module_fk.py", line 24, in main
    django.setup()
django.core.exceptions.ImproperlyConfigured: Cannot import 'leave'. Check that 'modules.leave.apps.LeaveConfig.name' is correct.
[exit 1]
### module boundaries (lint-imports)

╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘

Syntax error in modules/leave/domain/__init__.py, line 1: // empty
[exit 1]
```
