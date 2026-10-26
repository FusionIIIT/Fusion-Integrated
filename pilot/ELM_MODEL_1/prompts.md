# Prompt & Interaction Log: `qwen2.5-coder:14b` Trial

### Step 1: Foundation
Prompt:
"You are creating the Employee Leave Management (ELM) module inside Fusion ERP. Create `modules/elm/apps.py` and `modules/elm/registry.py` following the pattern in `modules/placement`."

### Step 2: ORM Models
Prompt:
"Based on the ELM Business Rules, generate `modules/elm/models.py` defining LeaveType, LeaveBalance, LeaveApplication, and SubstituteNomination."
*Observation*: Model emitted Django `ForeignKey(User)` for applicant and substitute references.

### Step 3: Domain Policy
Prompt:
"Create `modules/elm/domain/policy.py` containing pure Python logic for ELM entitlements (CL, RH, SCL, EL, VL, COL) with no Django or ORM imports."
*Observation*: Cleanly defined `LeaveCode` enum and `INSTITUTE_ENTITLEMENT_RULES` table without framework leaks.

### Step 4: Application Services
Prompt:
"Create `modules/elm/services/applications.py` with transactional workflows for submit_leave_application, record_substitute_response, and withdraw_application."

### Step 5: REST API
Prompt:
"Create `modules/elm/api/serializers.py`, `views.py`, and `urls.py` using DRF APIView and Fusion permissions (HasModuleGrant, HasPermission)."

### Step 6: App Registration
Prompt:
"Register `modules.elm` in `config/settings/base.py` and add its route in `config/urls.py`."

### Step 7: Migrations
Prompt:
"Generate the initial Django schema migration for ELM models."

### Step 8 & 9: Frontend Pages & Routes
Prompt:
"Create React components `LeaveBalance.tsx` and `LeaveApplication.tsx` and register them in `routes.tsx`."

### Step 10: Mechanical Integration Pass
*Action*: Adjusted integer `user_id` fields for zero-cross-module FK rule, verified URL include path, added `.importlinter` rules, and synchronized `registry/permissions.json`.
