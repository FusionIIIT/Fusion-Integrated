Employee Leave Management \(ELM\)

__Business Rule Specifications — Final Synchronized v1\.4__

Fusion ERP • Employee Leave Management • Synchronized baseline v1\.4

Rule discipline  
Business Rules externalize material policy, eligibility, authorization, calculation, routing, lifecycle, and threshold constraints\. They constrain actor\-triggered or event\-triggered Use Cases and workflow transitions; they are not workflow activities\. BR\-EL\-021 and BR\-EL\-026 remain retired identifiers for traceability\. BR\-EL\-030 uses current configured policy/hierarchy values; holiday/RH calendar publication semantics remain under BR\-EL\-031\.

# 1\. Business Rule Index

__BR ID__

__Rule Name__

__Type__

__Status__

__Related CFRs__

BR\-EL\-001

Supported leave\-category eligibility

Eligibility

Active

CFR\-EL\-002–003

BR\-EL\-002

Casual Leave entitlement and lapse

Entitlement

Active

CFR\-EL\-004, CFR\-EL\-028

BR\-EL\-003

Restricted Holiday entitlement and applicability

Entitlement / Calendar

Active

CFR\-EL\-005, CFR\-EL\-025, CFR\-EL\-028

BR\-EL\-004

Special Casual Leave entitlement and admissibility

Entitlement / Authority

Active

CFR\-EL\-006, CFR\-EL\-028

BR\-EL\-005

Non\-faculty Earned Leave credit and carry\-forward

Entitlement

Active

CFR\-EL\-007, CFR\-EL\-028

BR\-EL\-006

Faculty Vacation Leave entitlement and vacation\-period applicability

Entitlement / Calendar

Active

CFR\-EL\-008

BR\-EL\-007

VL\-to\-EL year\-end conversion

Calculation / Year\-end

Active

CFR\-EL\-008, CFR\-EL\-028

BR\-EL\-008

Treatment of EL created by VL conversion

Account

Active

CFR\-EL\-008, CFR\-EL\-028

BR\-EL\-009

Commuted Leave entitlement and treatment

Entitlement / Evidence

Active

CFR\-EL\-009, CFR\-EL\-028

BR\-EL\-010

Half\-day CL treatment

Calculation

Active

CFR\-EL\-004

BR\-EL\-011

Continuous\-day counting

Counting

Active

CFR\-EL\-003, CFR\-EL\-010

BR\-EL\-012

Applicant non\-overlap with half\-day CL exception

Validation

Active

CFR\-EL\-003

BR\-EL\-013

Station Leave coupling

Scope / Information

Active

CFR\-EL\-002

BR\-EL\-014

Substitute eligibility

Eligibility

Active

CFR\-EL\-011–012

BR\-EL\-015

Substitute consent gate and decline recovery

Routing / Eligibility

Active

CFR\-EL\-012

BR\-EL\-016

Unit Head final scope for CL/RH

Authority

Active

CFR\-EL\-013, CFR\-EL\-019

BR\-EL\-017

Unit Head recommendation for higher\-sanction leave

Authority / Routing

Active

CFR\-EL\-014, CFR\-EL\-019–020

BR\-EL\-018

Higher\-sanction routing

Routing

Active

CFR\-EL\-014, CFR\-EL\-019–020

BR\-EL\-019

Authority resolution and optional Establishment step

Routing / Authority

Active

CFR\-EL\-014, CFR\-EL\-019–020

BR\-EL\-020

Director self\-sanction

Authority / Exception

Active

CFR\-EL\-015

BR\-EL\-021

RETIRED — Modify Pending Request

Retired

RETIRED

—

BR\-EL\-022

Immediate withdrawal of pending request

Lifecycle

Active

CFR\-EL\-018

BR\-EL\-023

Cancellation of approved leave before start

Lifecycle / Routing

Active

CFR\-EL\-019

BR\-EL\-024

Fresh application after cancellation

Lifecycle

Active

CFR\-EL\-019

BR\-EL\-025

Extension of ongoing EL/COL/VL

Lifecycle / Calculation

Active

CFR\-EL\-020

BR\-EL\-026

RETIRED IDENTIFIER

Retired

RETIRED

—

BR\-EL\-027

Resumption applicability and review authority

Lifecycle / Authority

Active

CFR\-EL\-021

BR\-EL\-028

Normal, early, and late resumption outcome

Lifecycle / Account

Active

CFR\-EL\-021

BR\-EL\-029

Offline\-sanctioned leave synchronization

Record integrity

Active

CFR\-EL\-027

BR\-EL\-030

Current configured policy and hierarchy

Configuration

Active

CFR\-EL\-003, CFR\-EL\-014, CFR\-EL\-024

BR\-EL\-031

Effective published holiday/RH calendar

Calendar

Active

CFR\-EL\-003, CFR\-EL\-005, CFR\-EL\-025

BR\-EL\-032

SLA reminder on still\-pending task

Threshold / Notification

Active

CFR\-EL\-031

BR\-EL\-033

SLA escalation on still\-pending task

Threshold / Escalation

Active

CFR\-EL\-032

BR\-EL\-034

No post\-submission modification

Lifecycle constraint

Active

CFR\-EL\-017

BR\-EL\-035

Actionable task assignment notification

Notification

Active

CFR\-EL\-030

BR\-EL\-036

Role\-based authorization

Authorization

Active

CFR\-EL\-001

BR\-EL\-037

Administrative maintenance is not sanctioning

Authorization / Record integrity

Active

CFR\-EL\-026–027

BR\-EL\-038

Configurable SLA thresholds

Configuration

Active

CFR\-EL\-029

# 2\. Rule Specifications

## BR\-EL\-001 — Supported leave\-category eligibility

__Rule Type__

Eligibility

__Rule Statement__

A new leave request shall use only CL, RH, SCL, EL, COL, or VL and shall satisfy the category\-applicability conditions in the current configured ELM policy\.

__Applies To__

New leave validation

__Condition / Trigger__

Requested category/application context

__Required Outcome / Constraint__

Reject/prevent progression when category applicability is not satisfied\.

__Related CFRs__

CFR\-EL\-002–003

__Related Use Cases__

EL\-UC\-001, EL\-UC\-009

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-03

__Status / Revision Note__

Revised to remove published\-policy\-version semantics\.

## BR\-EL\-002 — Casual Leave entitlement and lapse

__Rule Type__

Entitlement

__Rule Statement__

Each employee has 8 CL days per year; unused CL lapses at year end and does not carry forward\.

__Applies To__

CL validation/year\-end

__Condition / Trigger__

CL account/request

__Required Outcome / Constraint__

Enforce 8\-day annual entitlement and no carry\-forward\.

__Related CFRs__

CFR\-EL\-004, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-001; EL\-UC\-020

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Active\.

## BR\-EL\-003 — Restricted Holiday entitlement and applicability

__Rule Type__

Entitlement / Calendar

__Rule Statement__

Each employee has 2 RH days per year; an RH request must correspond to an applicable Restricted Holiday in the currently effective published holiday/RH calendar; unused RH lapses at year end\.

__Applies To__

RH validation/year\-end

__Condition / Trigger__

RH request/account

__Required Outcome / Constraint__

Enforce entitlement, calendar applicability, and lapse\.

__Related CFRs__

CFR\-EL\-005, CFR\-EL\-025, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-001, EL\-UC\-015; EL\-UC\-020

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Expanded/confirmed after adjudication\.

## BR\-EL\-004 — Special Casual Leave entitlement and admissibility

__Rule Type__

Entitlement / Authority

__Rule Statement__

Each employee may use up to 15 SCL days per calendar year for a special purpose considered admissible by the applicable Sanctioning Authority; no separate encoded admissibility criterion is required; unused SCL lapses at year end\.

__Applies To__

SCL validation/decision/year\-end

__Condition / Trigger__

SCL request/account

__Required Outcome / Constraint__

Enforce annual limit; leave purpose is judged by authority; lapse unused SCL\.

__Related CFRs__

CFR\-EL\-006, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-001, EL\-UC\-005; EL\-UC\-020

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Clarified: admissibility is authority judgment, not separate encoded rule\.

## BR\-EL\-005 — Non\-faculty Earned Leave credit and carry\-forward

__Rule Type__

Entitlement

__Rule Statement__

Each non\-faculty employee shall receive 30 EL days per year and unused EL shall carry forward according to policy\.

__Applies To__

EL account/year\-end

__Condition / Trigger__

Non\-faculty EL

__Required Outcome / Constraint__

Credit 30/year and preserve unused EL across year boundary\.

__Related CFRs__

CFR\-EL\-007, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-001; EL\-UC\-020

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Active\.

## BR\-EL\-006 — Faculty Vacation Leave entitlement and vacation\-period applicability

__Rule Type__

Entitlement / Calendar

__Rule Statement__

Each faculty member shall have 60 VL associated with vacation periods supplied by the institute Academic Calendar, and VL may be availed only during an applicable vacation period\.

__Applies To__

VL validation

__Condition / Trigger__

Faculty VL request

__Required Outcome / Constraint__

Enforce 60 VL and external Academic Calendar vacation\-period applicability\.

__Related CFRs__

CFR\-EL\-008

__Related Use Cases__

EL\-UC\-001

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Clarified external vacation\-period source\.

## BR\-EL\-007 — VL\-to\-EL year\-end conversion

__Rule Type__

Calculation / Year\-end

__Rule Statement__

At year end, all unused faculty VL shall convert to EL at 2 VL : 1 EL including fractional conversion, and VL itself shall not carry forward\.

__Applies To__

Year\-end processing

__Condition / Trigger__

Unused faculty VL

__Required Outcome / Constraint__

Convert at 2:1 including fractions; leave no unused VL balance as VL\.

__Related CFRs__

CFR\-EL\-008, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-020

__Related Workflow\(s\)__

N/A

__Status / Revision Note__

Active, consolidated statement\.

## BR\-EL\-008 — Treatment of EL created by VL conversion

__Rule Type__

Account

__Rule Statement__

EL created by VL conversion shall be credited to the faculty member's EL balance, may carry forward, and may subsequently be availed\.

__Applies To__

Year\-end/account use

__Condition / Trigger__

Converted EL

__Required Outcome / Constraint__

Credit and retain converted EL as usable EL\.

__Related CFRs__

CFR\-EL\-008, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-020; EL\-UC\-001

__Related Workflow\(s\)__

N/A

__Status / Revision Note__

Active\.

## BR\-EL\-009 — Commuted Leave entitlement and treatment

__Rule Type__

Entitlement / Evidence

__Rule Statement__

Eligible employees have 20 COL days/year in this baseline; COL is medical/balance\-controlled, supporting medical evidence may be required where applicable, and unused COL carries forward\.

__Applies To__

COL validation/year\-end

__Condition / Trigger__

COL request/account

__Required Outcome / Constraint__

Enforce annual entitlement, balance/evidence conditions, and carry\-forward\.

__Related CFRs__

CFR\-EL\-009, CFR\-EL\-028

__Related Use Cases__

EL\-UC\-001; EL\-UC\-020

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Consolidated\.

## BR\-EL\-010 — Half\-day CL treatment

__Rule Type__

Calculation

__Rule Statement__

CL shall support first\-half and second\-half requests; an approved half day consumes 0\.5 CL day\.

__Applies To__

CL validation/accounting

__Condition / Trigger__

Half\-day CL

__Required Outcome / Constraint__

Recognize halves and deduct 0\.5 day when approved\.

__Related CFRs__

CFR\-EL\-004

__Related Use Cases__

EL\-UC\-001

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Active\.

## BR\-EL\-011 — Continuous\-day counting

__Rule Type__

Counting

__Rule Statement__

For EL, COL, and VL, intervening weekends and closed holidays inside the continuous approved interval count as leave days; this rule does not apply to CL, SCL, or RH\.

__Applies To__

Leave\-day calculation

__Condition / Trigger__

EL/COL/VL and excluded categories

__Required Outcome / Constraint__

Apply category\-specific counting boundary exactly\.

__Related CFRs__

CFR\-EL\-003, CFR\-EL\-010

__Related Use Cases__

EL\-UC\-001, EL\-UC\-009

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-03

__Status / Revision Note__

Active\.

## BR\-EL\-012 — Applicant non\-overlap with half\-day CL exception

__Rule Type__

Validation

__Rule Statement__

A new request shall not impermissibly overlap the employee's active pending or approved leave; first\-half and second\-half CL on the same date are non\-overlapping when they occupy different halves\.

__Applies To__

New\-request validation

__Condition / Trigger__

Employee leave intervals

__Required Outcome / Constraint__

Block impermissible overlap; permit different CL halves on same date\.

__Related CFRs__

CFR\-EL\-003

__Related Use Cases__

EL\-UC\-001

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Confirmed PS gap\.

## BR\-EL\-013 — Station Leave coupling

__Rule Type__

Scope / Information

__Rule Statement__

Station Leave permission/details, when applicable, shall be captured within the same leave application and shall not create a separate leave\-request process\.

__Applies To__

Leave application

__Condition / Trigger__

Outside\-Jabalpur context

__Required Outcome / Constraint__

Keep Station Leave inside associated leave application\.

__Related CFRs__

CFR\-EL\-002

__Related Use Cases__

EL\-UC\-001

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Active\.

## BR\-EL\-014 — Substitute eligibility

__Rule Type__

Eligibility

__Rule Statement__

When responsibility coverage is required, exactly one substitute is nominated; the substitute must be another employee, must not be the applicant, and must have no overlapping pending or approved leave during the responsibility period\.

__Applies To__

Substitute nomination

__Condition / Trigger__

Nominated employee and responsibility period

__Required Outcome / Constraint__

Reject an ineligible nominee\.

__Related CFRs__

CFR\-EL\-011–012

__Related Use Cases__

EL\-UC\-001, EL\-UC\-002, EL\-UC\-009, EL\-UC\-019

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-03

__Status / Revision Note__

Expanded to include not\-the\-applicant condition\.

## BR\-EL\-015 — Substitute consent gate and decline recovery

__Rule Type__

Routing / Eligibility

__Rule Statement__

Required approval routing shall not proceed until the nominated substitute accepts\. A decline leaves the consent gate closed; the applicant may nominate another eligible substitute or withdraw the pending request where applicable\.

__Applies To__

Substitute response

__Condition / Trigger__

Pending request requiring responsibility coverage

__Required Outcome / Constraint__

Accept releases routing gate; decline does not\.

__Related CFRs__

CFR\-EL\-012

__Related Use Cases__

EL\-UC\-002, EL\-UC\-019

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-03

__Status / Revision Note__

Expanded with adjudicated recovery path\.

## BR\-EL\-016 — Unit Head final scope for CL/RH

__Rule Type__

Authority

__Rule Statement__

For CL and RH, including associated Station Leave, the applicant's Unit Head is the final approve/reject authority except for the Director\-specific self\-sanction case\.

__Applies To__

New leave / same\-hierarchy cancellation

__Condition / Trigger__

CL/RH request

__Required Outcome / Constraint__

Final decision is made at Unit Head unless Director exception applies\.

__Related CFRs__

CFR\-EL\-013, CFR\-EL\-019

__Related Use Cases__

EL\-UC\-003, EL\-UC\-008

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-02

__Status / Revision Note__

Active\.

## BR\-EL\-017 — Unit Head recommendation for higher\-sanction leave

__Rule Type__

Authority / Routing

__Rule Statement__

For SCL, EL, COL, and VL, the Unit Head records Recommended or Not Recommended; Not Recommended is not a final rejection and both outcomes continue through the applicable higher\-sanction path\.

__Applies To__

Higher\-sanction new leave/extension/cancellation

__Condition / Trigger__

Higher\-sanction request

__Required Outcome / Constraint__

Record recommendation and continue routing\.

__Related CFRs__

CFR\-EL\-014, CFR\-EL\-019–020

__Related Use Cases__

EL\-UC\-003

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-02; CW\-EL\-03

__Status / Revision Note__

Clarified after adjudication\.

## BR\-EL\-018 — Higher\-sanction routing

__Rule Type__

Routing

__Rule Statement__

SCL, EL, COL, and VL requests requiring higher sanction shall proceed through the current configured hierarchy to the resolved final Sanctioning Authority\.

__Applies To__

Higher\-sanction contexts

__Condition / Trigger__

Routed request

__Required Outcome / Constraint__

Route to competent final authority using current configuration\.

__Related CFRs__

CFR\-EL\-014, CFR\-EL\-019–020

__Related Use Cases__

EL\-UC\-003–005

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-02; CW\-EL\-03

__Status / Revision Note__

Revised to current configuration terminology\.

## BR\-EL\-019 — Authority resolution and optional Establishment step

__Rule Type__

Routing / Authority

__Rule Statement__

The processing/sanctioning path shall be resolved from applicant, organizational unit, designation/role, leave category, and current hierarchy configuration; an Establishment step and the roles Deputy Registrar \(Estt\.\), Dean, Registrar, and Director occur only where configured\.

__Applies To__

Routing resolution

__Condition / Trigger__

Higher\-sanction request

__Required Outcome / Constraint__

Resolve and use only configured processing/authority steps\.

__Related CFRs__

CFR\-EL\-014, CFR\-EL\-019–020

__Related Use Cases__

EL\-UC\-003–005

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-02; CW\-EL\-03

__Status / Revision Note__

Revised to remove effective\-published\-policy wording\.

## BR\-EL\-020 — Director self\-sanction

__Rule Type__

Authority / Exception

__Rule Statement__

When the Director is the applicant, the Director\-specific self\-sanction path replaces the normal Unit Head/higher\-authority route\.

__Applies To__

Director\-applicant leave

__Condition / Trigger__

Applicant role = Director

__Required Outcome / Constraint__

Use Director self\-sanction path\.

__Related CFRs__

CFR\-EL\-015

__Related Use Cases__

EL\-UC\-001, EL\-UC\-005

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Active\.

## BR\-EL\-021 — RETIRED — Modify Pending Request

__Rule Type__

Retired

__Rule Statement__

The former rule permitting pending\-request modification is retired\. Post\-submission modification is not part of the synchronized baseline\.

__Applies To__

N/A

__Condition / Trigger__

N/A

__Required Outcome / Constraint__

N/A

__Related CFRs__

—

__Related Use Cases__

—

__Related Workflow\(s\)__

—

__Status / Revision Note__

Retired because G\-09 reversed the former semantics; replacement is BR\-EL\-034\.

## BR\-EL\-022 — Immediate withdrawal of pending request

__Rule Type__

Lifecycle

__Rule Statement__

A pending request may be withdrawn at any time before final approval; withdrawal is immediate, terminates remaining approval processing, blocks later approve/reject actions, and informs concerned roles\. After final approval, withdrawal is unavailable\.

__Applies To__

Pending request lifecycle

__Condition / Trigger__

Pending before final approval

__Required Outcome / Constraint__

Apply immediate terminal withdrawal effects\.

__Related CFRs__

CFR\-EL\-018

__Related Use Cases__

EL\-UC\-007

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Consolidated and strengthened\.

## BR\-EL\-023 — Cancellation of approved leave before start

__Rule Type__

Lifecycle / Routing

__Rule Statement__

An approved leave may be cancelled only before its start date; cancellation uses the same applicable hierarchy, does not edit the approved leave in place, approval marks the leave Cancelled and restores/adjusts already deducted balance, while rejection leaves the original approval unchanged\.

__Applies To__

Approved\-leave cancellation

__Condition / Trigger__

Approved and not started

__Required Outcome / Constraint__

Enforce pre\-start boundary and context\-specific final effects\.

__Related CFRs__

CFR\-EL\-019

__Related Use Cases__

EL\-UC\-008, EL\-UC\-003–005

__Related Workflow\(s\)__

CW\-EL\-02

__Status / Revision Note__

Expanded with adjudicated outcome effects\.

## BR\-EL\-024 — Fresh application after cancellation

__Rule Type__

Lifecycle

__Rule Statement__

If revised leave is still required after cancellation, a fresh leave application shall be submitted rather than editing the approved leave in place\.

__Applies To__

Approved\-leave change

__Condition / Trigger__

Successful cancellation followed by revised need

__Required Outcome / Constraint__

Require fresh application\.

__Related CFRs__

CFR\-EL\-019

__Related Use Cases__

EL\-UC\-008, EL\-UC\-001

__Related Workflow\(s\)__

CW\-EL\-02

__Status / Revision Note__

Active\.

## BR\-EL\-025 — Extension of ongoing EL/COL/VL

__Rule Type__

Lifecycle / Calculation

__Rule Statement__

Extension is available only for ongoing EL/COL/VL; it uses applicable eligibility, balance, substitute, calendar and sanction rules; approval posts only the incremental additional period while rejection preserves the original approved leave\.

__Applies To__

Ongoing leave extension

__Condition / Trigger__

Ongoing EL/COL/VL

__Required Outcome / Constraint__

Validate/rout appropriately and apply incremental\-only approval effect\.

__Related CFRs__

CFR\-EL\-020

__Related Use Cases__

EL\-UC\-009, EL\-UC\-002–005, EL\-UC\-019

__Related Workflow\(s\)__

CW\-EL\-03

__Status / Revision Note__

Expanded with adjudicated incremental\-posting rule\.

## BR\-EL\-026 — RETIRED IDENTIFIER

__Rule Type__

Retired

__Rule Statement__

No active rule is assigned to this identifier\.

__Applies To__

N/A

__Condition / Trigger__

N/A

__Required Outcome / Constraint__

N/A

__Related CFRs__

—

__Related Use Cases__

—

__Related Workflow\(s\)__

—

__Status / Revision Note__

Remains retired\.

## BR\-EL\-027 — Resumption applicability and review authority

__Rule Type__

Lifecycle / Authority

__Rule Statement__

Formal resumption review applies to EL, COL, and VL; the employee submits actual resumption information and the applicable Sanctioning Authority reviews it\.

__Applies To__

Resumption

__Condition / Trigger__

Return from EL/COL/VL

__Required Outcome / Constraint__

Route submitted resumption to applicable Sanctioning Authority\.

__Related CFRs__

CFR\-EL\-021

__Related Use Cases__

EL\-UC\-010–011

__Related Workflow\(s\)__

CW\-EL\-04

__Status / Revision Note__

Revised verifier identity\.

## BR\-EL\-028 — Normal, early, and late resumption outcome

__Rule Type__

Lifecycle / Account

__Rule Statement__

If actual resumption equals the approved end date, review causes no adjustment to approved leave period or balance\. If actual resumption is earlier or later, after review ELM records the actual leave period, adjusts leave balance accordingly, and synchronizes relevant leave/attendance records\.

__Applies To__

Resumption review

__Condition / Trigger__

Compare actual vs approved end date

__Required Outcome / Constraint__

Apply no\-adjustment or adjusted synchronization branch\.

__Related CFRs__

CFR\-EL\-021

__Related Use Cases__

EL\-UC\-011

__Related Workflow\(s\)__

CW\-EL\-04

__Status / Revision Note__

Major revision: no generic closure state; late resumption explicitly supported\.

## BR\-EL\-029 — Offline\-sanctioned leave synchronization

__Rule Type__

Record integrity

__Rule Statement__

Only leave already sanctioned through an authorized offline/paper process may be retrospectively recorded; sanction/reference evidence shall be captured, record consistency validated, relevant balance/history synchronized, and no second approval workflow initiated\.

__Applies To__

Offline leave entry

__Condition / Trigger__

Already\-sanctioned leave \+ acceptable ELM\-unavailable context

__Required Outcome / Constraint__

Synchronize records without new sanction\.

__Related CFRs__

CFR\-EL\-027

__Related Use Cases__

EL\-UC\-016

__Related Workflow\(s\)__

N/A

__Status / Revision Note__

Expanded with evidence and consistency requirements\.

## BR\-EL\-030 — Current configured policy and hierarchy

__Rule Type__

Configuration

__Rule Statement__

ELM validation and routing shall use the current configured leave\-policy parameters and hierarchy configuration\. No draft/publish/effective\-version lifecycle applies to leave\-policy parameters in this baseline\.

__Applies To__

Validation/routing/admin config

__Condition / Trigger__

Current configured values

__Required Outcome / Constraint__

Use current configuration directly; do not depend on policy publication state\.

__Related CFRs__

CFR\-EL\-003, CFR\-EL\-014, CFR\-EL\-024

__Related Use Cases__

EL\-UC\-001, EL\-UC\-003–005, EL\-UC\-014

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-02; CW\-EL\-03

__Status / Revision Note__

Materially revised from former 'Effective Policy Version' rule\.

## BR\-EL\-031 — Effective published holiday/RH calendar

__Rule Type__

Calendar

__Rule Statement__

Date and RH validation shall use the currently effective published holiday/RH calendar until a replacement calendar is published\.

__Applies To__

Date/RH validation

__Condition / Trigger__

Published calendar state

__Required Outcome / Constraint__

Use current published calendar; activate replacement only when published\.

__Related CFRs__

CFR\-EL\-003, CFR\-EL\-005, CFR\-EL\-025

__Related Use Cases__

EL\-UC\-001, EL\-UC\-015

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

Confirmed after adjudication\.

## BR\-EL\-032 — SLA reminder on still\-pending task

__Rule Type__

Threshold / Notification

__Rule Statement__

When an SLA\-controlled actionable task reaches its configured reminder threshold, issue a reminder to the responsible user and log it only if the task is still pending; otherwise issue no reminder\.

__Applies To__

EL\-UC\-021 / SLA reminder\-threshold processing

__Condition / Trigger__

Task at reminder threshold

__Required Outcome / Constraint__

Pending \-> remind\+log; non\-pending \-> no reminder\.

__Related CFRs__

CFR\-EL\-031

__Related Use Cases__

EL\-UC\-021

__Related Workflow\(s\)__

N/A — reminder alone does not create a workflow transition\.

__Status / Revision Note__

Strengthened with pending\-only guard\.

## BR\-EL\-033 — SLA escalation on still\-pending task

__Rule Type__

Threshold / Escalation

__Rule Statement__

When an SLA\-controlled actionable task remains pending past its configured escalation threshold, the system shall perform the configured escalation action: notify the configured higher/responsible authority and, where the escalation configuration changes routing/responsibility, apply that routing/responsibility change; the escalation action shall be logged\. If the task is no longer pending, no escalation shall be issued\.

__Applies To__

EL\-UC\-021 / SLA escalation\-threshold processing

__Condition / Trigger__

Task past escalation threshold

__Required Outcome / Constraint__

Pending \-> configured notify/escalate action \+ log; non\-pending \-> no escalation\.

__Related CFRs__

CFR\-EL\-032

__Related Use Cases__

EL\-UC\-021

__Related Workflow\(s\)__

Conditional cross\-cutting trace to the applicable CW\-EL\-01–04 only when escalation changes routing/responsibility; notification\-only escalation = N/A\.

__Status / Revision Note__

Pending\-only guard retained; notification\-only and routing/responsibility\-changing escalation are distinguished formally\.

## BR\-EL\-034 — No post\-submission modification

__Rule Type__

Lifecycle constraint

__Rule Statement__

A submitted pending leave request shall not be modified in place\. If change is needed before final approval, the employee may withdraw and submit a new application if needed\.

__Applies To__

Pending request

__Condition / Trigger__

Submitted and pending

__Required Outcome / Constraint__

Block in\-place modification; preserve withdrawal/new\-application route\.

__Related CFRs__

CFR\-EL\-017

__Related Use Cases__

EL\-UC\-007, EL\-UC\-001

__Related Workflow\(s\)__

CW\-EL\-01

__Status / Revision Note__

New replacement rule for retired BR\-EL\-021\.

## BR\-EL\-035 — Actionable task assignment notification

__Rule Type__

Notification

__Rule Statement__

When an actionable workflow task is assigned to a user, ELM shall notify the assigned user\.

__Applies To__

Task assignment

__Condition / Trigger__

New actionable assignment

__Required Outcome / Constraint__

Generate assignment notification\.

__Related CFRs__

CFR\-EL\-030

__Related Use Cases__

EL\-UC\-002–005, EL\-UC\-011; EL\-UC\-021

__Related Workflow\(s\)__

CW\-EL\-01; CW\-EL\-02; CW\-EL\-03; CW\-EL\-04

__Status / Revision Note__

New explicit rule from adjudicated PS\.

## BR\-EL\-036 — Role\-based authorization

__Rule Type__

Authorization

__Rule Statement__

ELM capabilities shall be available only to users authorized for the corresponding employee, processing, sanctioning, or administrative role\.

__Applies To__

All protected ELM actions

__Condition / Trigger__

Attempted protected action

__Required Outcome / Constraint__

Permit only role\-authorized action\.

__Related CFRs__

CFR\-EL\-001

__Related Use Cases__

All actor UCs

__Related Workflow\(s\)__

All composite workflows

__Status / Revision Note__

New explicit cross\-cutting rule from PS\.

## BR\-EL\-037 — Administrative maintenance is not sanctioning

__Rule Type__

Authorization / Record integrity

__Rule Statement__

Authorized leave\-record maintenance/correction shall not itself create a new sanctioning decision; retrospective offline entry is also synchronization rather than a second approval\.

__Applies To__

Administrative record maintenance

__Condition / Trigger__

Admin maintenance action

__Required Outcome / Constraint__

Preserve separation between record maintenance and sanctioning\.

__Related CFRs__

CFR\-EL\-026–027

__Related Use Cases__

EL\-UC\-016–017

__Related Workflow\(s\)__

N/A

__Status / Revision Note__

New explicit cross\-cutting distinction\.

## BR\-EL\-038 — Configurable SLA thresholds

__Rule Type__

Configuration

__Rule Statement__

Reminder and escalation thresholds for SLA\-controlled actionable workflow tasks shall be configurable by an authorized administrative role and shall govern EL\-UC\-021 event\-triggered SLA processing\.

__Applies To__

SLA configuration

__Condition / Trigger__

Authorized threshold change

__Required Outcome / Constraint__

Store valid thresholds and use them in EL\-UC\-021\.

__Related CFRs__

CFR\-EL\-029

__Related Use Cases__

EL\-UC\-018; EL\-UC\-021

__Related Workflow\(s\)__

N/A

__Status / Revision Note__

New explicit configuration rule\.

