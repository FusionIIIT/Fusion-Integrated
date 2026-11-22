# Assignment 7 - Prompts & Interaction Log (Qwen2.5-Coder:1.5B)

## Details
- **Student**: Nikhil Jain (24BCS170)
- **Module**: Super Admin (Module 23)
- **Chosen Workflow**: BW-SA-08 (Archived User Reversibility Window Expiry)
- **Model**: Qwen2.5-Coder:1.5B (via Ollama in WSL 2)

---

### Prompt 1: Model & Architecture Constraints
```text
@codebase Generate the Django models for Super Admin under modules/superadmin/models.py.
Include UserAccount, RoleAssignment, and AuditEntry.
Enforce ADR-0013: use plain integer IDs for user references; do not use cross-module ForeignKeys.
```
- **Outcome**: Produced `UserAccount`, `RoleAssignment`, and `AuditEntry` with integer IDs.

### Prompt 2: Domain Business Rules
```text
Implement pure-Python domain rules in modules/superadmin/domain/policy.py.
Validate institute email (BR-SA-002), archival eligibility (BR-SA-004), reversibility window (BR-SA-005), role dating (BR-SA-008), and singular role occupancy (BR-SA-007).
```
- **Outcome**: Generated validation rules without framework imports, passing import-linter.

### Prompt 3: DRF API Endpoints
```text
Generate DRF serializers, views, and urls under modules/superadmin/api/ with HasPermission RBAC guards.
```
- **Outcome**: Implemented endpoints for user lifecycle, role management, and audit log inspection.

### Prompt 4: Frontend & Manifest
```text
Generate client route client/src/modules/superadmin/routes.tsx and register under /superadmin.
```
- **Outcome**: Registered client navigation and synced permission manifest.
