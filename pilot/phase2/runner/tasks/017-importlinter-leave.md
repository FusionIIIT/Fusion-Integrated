TITLE: Put the leave module under Fusion's import-linter contracts
FORMAT: diff
EDIT: .importlinter
READ: kit:phase2/DESIGN.md
LIMIT: 600
POST: none
---
Review finding: lint-imports passes on the Phase-1 code only because .importlinter never mentions modules.leave. Phase 1 imported modules.directory.models from inside leave, which the first contract exists to forbid, and nothing caught it. Add leave to the existing contracts and give it the same layering contract that placement has. Fix only this, with SEARCH/REPLACE edits in .importlinter:

1. In [importlinter:contract:modules-only-touch-contracts], add `    modules.leave` as the last line of source_modules (after `    modules.accesscontrol`), and add these five lines at the end of forbidden_modules (after `    modules.accesscontrol.models`):
    modules.leave.models
    modules.leave.services
    modules.leave.selectors
    modules.leave.api
    modules.leave.domain

2. In [importlinter:contract:domain-is-pure-python], add `    modules.leave.domain` to source_modules directly after `    modules.placement.domain`.

3. At the end of the file add a blank line and this contract:
[importlinter:contract:leave-layers]
name = Layering inside leave
type = layers
layers =
    modules.leave.api
    modules.leave.services
    modules.leave.selectors
    modules.leave.models
    modules.leave.domain

Do not change anything else.
