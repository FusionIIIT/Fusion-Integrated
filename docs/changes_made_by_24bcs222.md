# Changes Made by 24BCS222 — ELM Phase 2 Engineering Log

## 1. Student and Environment Configuration

- **Student Roll Number:** 24BCS222
- **Repository:** `Fusion-Integrated`
- **Fork:** https://github.com/uttkarshbagad/Fusion-Integrated
- **Branch:** `elm-phase2`
- **Module:** Employee Leave Management (ELM)
- **Hardware:** Intel Core i3-1115G4 @ 3.00 GHz, 8 GB RAM, Intel UHD Graphics
- **AI Coding Model:** Qwen2.5-Coder 7B via Ollama *(confirm this matches the model you used for your Phase 2 changes)*
- **Coding Interface:** VS Code with AI coding assistance *(update if needed)*

---

## 2. Phase 2 Objective

The objective of Phase 2 was to review and improve the Employee Leave Management (ELM) module by addressing gaps in functionality, authorization, and user experience.

My contributions focused on two areas:

1. Adding a Leave Application History page so users can view their submitted leave applications.
2. Restricting leave application withdrawal to the employee who owns the application, strengthening authorization and preventing unauthorized actions.

---

## 3. Commit-by-Commit Engineering Log

### Commit 1 — Add ELM Leave Application History

**Commit message:** `Add ELM leave application history`

**Area:** Frontend integration and leave application tracking

**Objective:** Provide users with a dedicated page to view their leave application history.

**Implementation details:**

- Added a `LeaveHistory.tsx` component under `client/src/modules/elm/`.
- Integrated the page with the ELM application API to retrieve leave application records.
- Displayed leave application information in a dedicated history view.
- Added support for withdrawing eligible leave applications through the existing withdrawal API.
- Connected the page to the frontend routing so users can navigate to their leave history.
- Used the existing project API infrastructure to maintain consistency with the Fusion ERP frontend.

**AI-assisted development approach:**

The implementation was developed incrementally by examining the existing ELM frontend, API utilities, and route configuration before adding the history page.

The changes were reviewed to ensure that the new component followed the existing project structure and interacted with the available API endpoints.

**Files involved:**

- `client/src/modules/elm/LeaveHistory.tsx`
- `client/src/modules/elm/api.ts`
- `client/src/modules/elm/routes.tsx`

**Expected verification:**

- Confirm that the Leave History page loads successfully.
- Verify that application records are fetched from the ELM API.
- Check that the page handles loading, empty, and error states appropriately, if implemented.
- Verify that the withdrawal action is available only when permitted by the application workflow.

---

### Commit 2 — Restrict Leave Withdrawal to the Applicant

**Commit message:** `fix(elm): restrict leave withdrawal to applicant`

**Area:** Backend authorization and access control

**Objective:** Ensure that an employee cannot withdraw a leave application belonging to another employee.

**Problem addressed:**

Without an ownership check, an authenticated user might attempt to withdraw another employee's leave application by submitting a withdrawal request using that application's identifier. This could lead to unauthorized changes to leave records.

**Implementation details:**

- Updated the leave withdrawal handling to enforce application ownership.
- Ensured that the user requesting withdrawal is checked against the applicant associated with the leave application.
- Prevented users from withdrawing applications that belong to other employees.
- Retained the existing workflow validation for determining whether an application is eligible for withdrawal.
- Strengthened server-side authorization rather than relying only on frontend visibility or restrictions.

**Security significance:**

The backend must independently validate ownership for every withdrawal request. Hiding a withdrawal button in the frontend is not sufficient because API endpoints can be called directly.

The ownership restriction therefore helps protect the integrity of employee leave records and prevents unauthorized workflow actions.

**Expected verification:**

- Confirm that the applicant can withdraw their own eligible application.
- Confirm that a different user cannot withdraw that application.
- Verify that applications in workflow states that do not permit withdrawal remain protected by the existing transition rules.
- Confirm that unauthorized requests return an appropriate error response and do not modify the application status.

---

## 4. Engineering Validation

The following checks should be used to validate the changes on the final `elm-phase2` branch.

| Check | Expected result |
|---|---|
| Leave History page | Loads without frontend errors |
| Application API integration | Displays the returned application records |
| Applicant withdrawal | Permitted for an eligible application |
| Unauthorized withdrawal | Blocked for a different user |
| Workflow validation | Invalid status transitions are rejected |
| Frontend build | Completes successfully |
| TypeScript type check | Completes without errors |
| Django system check | Completes without errors |
| Existing ELM policy tests | Continue to pass |

**Testing evidence:** Record the actual results after running the checks on the final branch. Do not mark a check as passed unless it has been executed and verified.

Suggested commands, from the appropriate project directories:

```bash
# Backend: run from the directory containing manage.py
python manage.py check
pytest modules/elm/tests/test_policy.py

# Frontend: run from the client directory
npm run build
npm run typecheck
```

If the project uses a different pytest setup or command, use the command specified by its existing configuration.

---

## 5. Engineering Lessons

### 5.1 Frontend Functionality Must Be Connected to the Backend

Adding a history page involves more than creating a React component. It must retrieve real application data, integrate with the existing API client, and be registered in the frontend routes.

### 5.2 Authorization Must Be Enforced on the Server

Frontend controls alone cannot protect sensitive actions. The backend must verify that the requester owns the application before allowing withdrawal.

### 5.3 Workflow Rules and Ownership Checks Serve Different Purposes

Workflow validation determines whether an application can transition to a target status. Ownership validation determines whether the requesting user is authorized to perform the action. Both checks are important for a secure leave management system.

### 5.4 Incremental Changes Make AI-Assisted Development Easier to Review

Working in small, focused changes makes it easier to inspect diffs, identify integration issues, and understand the effect of each commit. Human review remains essential when using AI-generated code.

---

## 6. Summary and Conclusion

My Phase 2 contributions to the Employee Leave Management module focused on improving application tracking and strengthening authorization.

The first commit added a Leave Application History page and integrated it with the existing ELM frontend and API structure. The second commit introduced an applicant-ownership restriction for leave withdrawal, helping prevent unauthorized changes to employee records.

Together, these changes improve the usability and security of the ELM module. Final verification should confirm that the frontend builds correctly, existing policy tests pass, and both authorized and unauthorized withdrawal scenarios behave as expected.

---

## Appendix: Evidence and References

1. Repository: https://github.com/uttkarshbagad/Fusion-Integrated
2. Branch: `elm-phase2`
3. Reference engineering log: `docs/changes_made_by_24bcs260.md`
4. Commit messages:
   - `Add ELM leave application history`
   - `fix(elm): restrict leave withdrawal to applicant`
5. Relevant implementation files:
   - `client/src/modules/elm/LeaveHistory.tsx`
   - `client/src/modules/elm/api.ts`
   - `client/src/modules/elm/routes.tsx`
   - Backend ELM withdrawal API and associated authorization logic

