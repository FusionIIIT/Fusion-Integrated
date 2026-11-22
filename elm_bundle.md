# Employee Leave Management (ELM) Integration Specification

## 1. Core Domain & Data Models
* **Leave Categories & Entitlements:**
  * **CL (Casual Leave):** 8 days/year, no carry-forward. Supports half-days (0.5 deduction). Continuous-day counting does *not* apply[cite: 3, 4].
  * **RH (Restricted Holiday):** 2 days/year, no carry-forward. Must match effective published RH calendar[cite: 3, 4].
  * **SCL (Special Casual Leave):** Up to 15 days/year, no carry-forward. Admissibility decided by authority[cite: 3, 4].
  * **EL (Earned Leave):** 30 days/year for non-faculty. Unused EL carries forward. Continuous-day counting applies (weekends/holidays inside interval count as leave)[cite: 3, 4].
  * **VL (Vacation Leave):** 60 days for faculty based on Academic Calendar. No carry-forward; unused VL converts to EL at year-end (2 VL : 1 EL)[cite: 3, 4].
  * **COL (Commuted Leave):** 20 days/year. Requires medical evidence; carries forward. Continuous-day counting applies[cite: 3, 4].
* **Station Leave:** Captured within the same leave application if the employee leaves Jabalpur; not a separate process[cite: 3, 4].
* **Roles:** Employee, Substitute (Responsibility Holder), Unit Head, Establishment (Deputy Registrar), Dean, Registrar, Director, Leave Administrator[cite: 3].

## 2. Core State Machine & Workflows
All leaves follow variations of these strict state transitions[cite: 1]:
1. **Draft / Not Submitted:** Initial state[cite: 1].
2. **Awaiting Substitute Response:** If substitute is required, they must Accept to release the routing gate. If Declined, state moves to **Applicant Action Required** for replacement nomination[cite: 1, 4].
3. **Awaiting Unit Head Review:** 
   * For CL/RH: Unit Head gives final `Approve` or `Reject`[cite: 1, 3].
   * For SCL/EL/COL/VL: Unit Head records `Recommended` or `Not Recommended` (which is not a rejection) and routes forward[cite: 1, 3].
4. **Awaiting Establishment Routing:** Optional configured step for higher-sanction verification[cite: 1, 3].
5. **Awaiting Final Sanction Decision:** Final authority (Dean/Registrar/Director) records `Approve` or `Reject`[cite: 1, 3].
* **Director Exception:** If the Director is the applicant, they use a self-sanction path bypassing Unit Head[cite: 1, 4].

## 3. Lifecycle Actions & APIs (Use Cases)
* **Withdraw (EL-UC-007):** A pending request can be withdrawn immediately at any time *before* final approval. Terminates all routing[cite: 2, 4].
* **Cancel (EL-UC-008):** Approved leave can only be cancelled *before* the start date. Routes through original hierarchy. If approved, balance is restored; original leave is NOT edited in place[cite: 2, 4].
* **Extend (EL-UC-009):** Only for ongoing EL/COL/VL. Approvals post *incremental* additional periods without modifying the original record[cite: 2, 4].
* **Resume (EL-UC-010/011):** For EL/COL/VL. Employee submits actual return date. If early/late, Sanctioning Authority reviews, system calculates actual period, adjusts balance, and syncs attendance[cite: 2, 4].
* **Offline Leave (EL-UC-016):** Admins can retrospectively sync authorized offline/paper leave without triggering a new approval workflow[cite: 2, 4].
* **Year-End Processing (EL-UC-020):** Event-triggered. Lapses CL/RH/SCL, converts VL to EL, carries forward EL/COL[cite: 2, 4].

## 4. Key Business Rules (Validation)
* **Overlap Guard (BR-EL-012):** New requests cannot overlap with active pending/approved leave. Exception: First-half and second-half CL on the same date are allowed[cite: 4].
* **Substitute Guard (BR-EL-014):** Nominee must be an employee, cannot be the applicant, and cannot have overlapping pending/approved leave[cite: 4].
* **Immutable Pending State (BR-EL-034):** Submitted requests cannot be modified in place. The user must withdraw and submit a new application[cite: 4].
* **Role-Based Auth (BR-EL-036):** All APIs must strictly validate role authorizations[cite: 4].

## 5. Fusion ERP Integration Directives
* **Auth & Roles:** Use existing Fusion authentication and role-management decorators/middleware.
* **UI/UX:** Inherit common Fusion layouts, navigation, and reusable UI components. Do not build a standalone portal.
* **Database:** Extend the existing Fusion database schema. Create normalized tables for `elm_leave_requests`, `elm_leave_balances`, `elm_substitute_logs`, and `elm_state_transitions`.```