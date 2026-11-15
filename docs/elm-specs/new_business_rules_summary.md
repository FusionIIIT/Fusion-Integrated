# Employee Leave Management (ELM) Business Rules Summary

## BR-EL-001: Supported leave-category eligibility
- **Type:** Eligibility
- **Status:** Active
- **Description:** Ensures that leave requests are made using only specific categories (CL, RH, SCL, EL, COL, VL) and that they comply with the current policy.

## BR-EL-002: Casual Leave entitlement and lapse
- **Type:** Entitlement
- **Status:** Active
- **Description:** Employees are entitled to 8 CL days per year, which lapse at year-end and do not carry forward.

## BR-EL-003: Restricted Holiday entitlement and applicability
- **Type:** Entitlement / Calendar
- **Status:** Active
- **Description:** Employees are entitled to 2 RH days per year, which must correspond to applicable Restricted Holidays in the current holiday calendar and lapse at year-end.

## BR-EL-004: Special Casual Leave entitlement and admissibility
- **Type:** Entitlement / Authority
- **Status:** Active
- **Description:** Employees may use up to 15 SCL days per year for special purposes, which are judged by the Sanctioning Authority and lapse at year-end.

## BR-EL-005: Non-faculty Earned Leave credit and carry-forward
- **Type:** Entitlement
- **Status:** Active
- **Description:** Non-faculty employees receive 30 EL days per year, which carry forward according to policy.

## BR-EL-006: Faculty Vacation Leave entitlement and vacation-period applicability
- **Type:** Entitlement / Calendar
- **Status:** Active
- **Description:** Faculty members are entitled to 60 VL days during vacation periods as per the institute's Academic Calendar.

## BR-EL-007: VL-to-EL year-end conversion
- **Type:** Calculation / Year-end
- **Status:** Active
- **Description:** Unused faculty VL is converted to EL at a ratio of 2:1, and unused VL is not carried forward.

## BR-EL-008: Treatment of EL created by VL conversion
- **Type:** Account
- **Status:** Active
- **Description:** EL created by VL conversion is credited to the employee's EL balance, may carry forward, and can be availed.

## BR-EL-009: Commuted Leave entitlement and treatment
- **Type:** Entitlement / Evidence
- **Status:** Active
- **Description:** Employees are entitled to 20 COL days per year, which are medical/balance-controlled and may require supporting evidence.

## BR-EL-010: Half-day CL treatment
- **Type:** Calculation
- **Status:** Active
- **Description:** CL requests can be for half-days, and each approved half-day consumes 0.5 CL day.

## BR-EL-011: Continuous-day counting
- **Type:** Counting
- **Status:** Active
- **Description:** For EL, COL, and VL, intervening weekends and closed holidays inside the continuous approved interval count as leave days.

## BR-EL-012: Applicant non-overlap with half-day CL exception
- **Type:** Validation
- **Status:** Active
- **Description:** New leave requests must not overlap with the employee's active pending or approved leave.

## BR-EL-013: Station Leave coupling
- **Type:** Scope / Information
- **Status:** Active
- **Description:** Station Leave details must be captured within the same leave application.

## BR-EL-014: Substitute eligibility
- **Type:** Eligibility
- **Status:** Active
- **Description:** When responsibility coverage is required, exactly one substitute must be nominated and must have no overlapping leave during the responsibility period.

## BR-EL-015: Substitute consent gate and decline recovery
- **Type:** Routing / Eligibility
- **Status:** Active
- **Description:** Required approval routing must not proceed until the nominated substitute accepts.

## BR-EL-016: Unit Head final scope for CL/RH
- **Type:** Authority
- **Status:** Active
- **Description:** For CL and RH, including associated Station Leave, the applicant's Unit Head is the final approve/reject authority.

## BR-EL-017: Unit Head recommendation for higher-sanction leave
- **Type:** Authority / Routing
- **Status:** Active
- **Description:** For SCL, EL, COL, and VL, the Unit Head records Recommended or Not Recommended.

## BR-EL-018: Higher-sanction routing
- **Type:** Routing
- **Status:** Active
- **Description:** SCL, EL, COL, and VL requests requiring higher sanction proceed through the current configured hierarchy.

## BR-EL-019: Authority resolution and optional Establishment step
- **Type:** Routing / Authority
- **Status:** Active
- **Description:** The processing/sanctioning path is resolved from applicant, organizational unit, designation/role, leave category, and current hierarchy configuration.

## BR-EL-020: Director self-sanction
- **Type:** Authority / Exception
- **Status:** Active
- **Description:** When the Director is the applicant, the Director-specific self-sanction path replaces the normal Unit Head/higher-authority route.

## BR-EL-022: Immediate withdrawal of pending request
- **Type:** Lifecycle
- **Status:** Active
- **Description:** A pending request may be withdrawn at any time before final approval.

## BR-EL-023: Cancellation of approved leave before start
- **Type:** Lifecycle / Routing
- **Status:** Active
- **Description:** An approved leave may be cancelled only before its start date.

## BR-EL-024: Fresh application after cancellation
- **Type:** Lifecycle
- **Status:** Active
- **Description:** If revised leave is still required after cancellation, a fresh leave application must be submitted.

## BR-EL-025: Extension of ongoing EL/COL/VL
- **Type:** Lifecycle / Calculation
- **Status:** Active
- **Description:** Extension is available only for ongoing EL/COL/VL.

## BR-EL-027: Resumption applicability and review authority
- **Type:** Lifecycle / Authority
- **Status:** Active
- **Description:** Formal resumption review applies to EL, COL, and VL.

## BR-EL-028: Normal, early, and late resumption outcome
- **Type:** Lifecycle / Account
- **Status:** Active
- **Description:** If actual resumption equals the approved end date, no adjustment is made. If actual resumption is earlier or later, ELM records the actual leave period and adjusts the balance accordingly.

## BR-EL-029: Offline-sanctioned leave synchronization
- **Type:** Record integrity
- **Status:** Active
- **Description:** Only leave sanctioned through an authorized offline process may be retrospectively recorded.

## BR-EL-030: Current configured policy and hierarchy
- **Type:** Configuration
- **Status:** Active
- **Description:** ELM validation and routing use the current configured leave-policy parameters and hierarchy configuration.

## BR-EL-031: Effective published holiday/RH calendar
- **Type:** Calendar
- **Status:** Active
- **Description:** Date and RH validation use the currently effective published holiday calendar.

## BR-EL-032: SLA reminder on still-pending task
- **Type:** Threshold / Notification
- **Status:** Active
- **Description:** When an SLA-controlled actionable task reaches its reminder threshold, a reminder is issued to the responsible user.

## BR-EL-033: SLA escalation on still-pending task
- **Type:** Threshold / Escalation
- **Status:** Active
- **Description:** When an SLA-controlled actionable task remains pending past its escalation threshold, the system performs the configured escalation action.

## BR-EL-034: No post-submission modification
- **Type:** Lifecycle constraint
- **Status:** Active
- **Description:** A submitted pending leave request shall not be modified in place.

## BR-EL-035: Actionable task assignment notification
- **Type:** Notification
- **Status:** Active
- **Description:** When an actionable workflow task is assigned to a user, ELM notifies the assigned user.

## BR-EL-036: Role-based authorization
- **Type:** Authorization
- **Status:** Active
- **Description:** ELM capabilities are available only to users authorized for the corresponding employee, processing, sanctioning, or administrative role.

## BR-EL-037: Administrative maintenance is not sanctioning
- **Type:** Authorization / Record integrity
- **Status:** Active
- **Description:** Authorized leave-record maintenance/correction shall not create a new sanctioning decision.

## BR-EL-038: Configurable SLA thresholds
- **Type:** Configuration
- **Status:** Active
- **Description:** Reminder and escalation thresholds for SLA-controlled actionable workflow tasks are configurable.
