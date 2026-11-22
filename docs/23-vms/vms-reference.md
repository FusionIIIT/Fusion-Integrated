# VMS Specification Reference & Requirement Mapping

This document maps all live requirements (CFRs, AFRs), Use Cases (UCs), Business Rules (BRs), and Workflows (WFs) to their implementation and verification files in `Fusion-Integrated`.

---

## 1. Core Functional Requirements (CFR / AFR)

| Requirement ID | Description | Primary Enforcement | Verification Suite |
|----------------|-------------|----------------------|--------------------|
| VMS-CFR-001 | Single authoritative digital system for visitor records | `modules/vms/models/visitor.py`, `services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_001` |
| VMS-AFR-002 | Authoritative queryable visitor registry | `modules/vms/selectors/visitors.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_002` |
| VMS-CFR-002 | Role assignment & duration governance | `modules/vms/services/roles.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_003` |
| VMS-AFR-003 | Pending work handoff on role reassignment | `modules/vms/services/roles.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_004` |
| VMS-CFR-003 | Integration boundaries & zero cross-module FKs | `modules/vms/contracts.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_006` |
| VMS-AFR-007 | Event / hostel metadata coordination | `modules/vms/models/visitor.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_007` |
| VMS-CFR-004 | Super Admin VIP permissions management | `modules/vms/services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_008` |
| VMS-AFR-005 | VIP bypass of manual host approval | `modules/vms/domain/state_machine.py`, `services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_009` |
| VMS-CFR-005 | Operational audit trail logging | `modules/vms/models/visitor.py` (`GateCheckLog`), `services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_010` |
| VMS-AFR-006 | Audit trail querying and filtering | `modules/vms/selectors/audit.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_011` |
| VMS-CFR-006 | Access policy versioning | `modules/vms/models/policy.py`, `services/policy.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_012` |
| VMS-AFR-008 | Active published policy runtime enforcement | `modules/vms/domain/validation.py`, `services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_013` |
| VMS-CFR-007 | Blacklist and safe-list registry | `modules/vms/models/blacklist.py`, `services/blacklist.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_014` |
| VMS-AFR-009 | Blacklist check rejection | `modules/vms/domain/blacklist.py`, `services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_015` |
| VMS-AFR-010 | Safe-list override of watchlist match | `modules/vms/domain/blacklist.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_016` |
| VMS-CFR-008 | Visitor reports and analytics | `modules/vms/selectors/analytics.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_017` |
| VMS-CFR-009 | Bulk visitor management for events | `modules/vms/services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_018` |
| VMS-CFR-010 | Mandatory pre-registration fields | `modules/vms/domain/validation.py`, `api/serializers.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_019` |
| VMS-AFR-011 | Duplicate visit request prevention | `modules/vms/domain/validation.py`, `services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_020` |
| VMS-CFR-011 | Digital pass QR generation and status | `modules/vms/domain/qr_crypto.py`, `models/visitor.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_021` |
| VMS-CFR-012 | Host approval / rejection decisions | `modules/vms/services/approval.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_022` |
| VMS-AFR-012 | Host pre-authorization for frequent visitors | `modules/vms/models/visitor.py`, `services/approval.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_023` |
| VMS-CFR-013 | Security gate validation and check-in | `modules/vms/services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_024` |
| VMS-AFR-013 | Expired pass gate rejection | `modules/vms/domain/validation.py`, `services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_025` |
| VMS-CFR-014 | Manual gate override authorization & audit | `modules/vms/services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_026` |
| VMS-CFR-015 | Security gate check-out & visit completion | `modules/vms/services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_027` |
| VMS-CFR-016 | Live on-site visitor dashboard roster | `modules/vms/selectors/visitors.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_028` |
| VMS-CFR-017 | Zone access authorization checking | `modules/vms/services/zone.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_029` |
| VMS-AFR-014 | Temporary time-boxed zone elevation | `modules/vms/services/zone.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_030` |
| VMS-CFR-018 | Emergency muster roll-call snapshot | `modules/vms/services/emergency.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_031` |
| VMS-AFR-015 | Emergency roll-call accountability tracking | `modules/vms/services/emergency.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_032` |
| VMS-CFR-019 | Offline gate reconciliation | `modules/vms/services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_033` |
| VMS-CFR-020 | Security walk-in registration | `modules/vms/services/registration.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_034` |
| VMS-AFR-016 | Walk-in contingency approval SLA | `modules/vms/services/approval.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_035` |
| VMS-CFR-021 | Visit extension and early termination | `modules/vms/services/approval.py`, `services/gate.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_036` |
| VMS-AFR-017 | Early termination immediate pass revocation | `modules/vms/services/approval.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_037` |
| VMS-CFR-022 | Periodic background expiry & auto checkout | `modules/vms/services/scheduled.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_038` |
| VMS-AFR-018 | Overstay detection and automatic checkout | `modules/vms/services/scheduled.py` | `modules/vms/tests/spec/fr/test_fr.py::test_fr_039` |

---

## 2. Business Rules (BR Mapping)

All 47 business rules are enforced in `modules/vms/domain/` and checked in service transitions:

| Rule ID | Rule Name | Domain Enforcement File | Test Name |
|---------|-----------|-------------------------|-----------|
| VMS-BR-037 | Mandatory Pre-registration Validation | `domain/validation.py` | `test_br_037` |
| VMS-BR-038 | Duplicate Visit Request Check | `domain/validation.py` | `test_br_038` |
| VMS-BR-049 | Walk-in Contingency Approval Authorization | `domain/state_machine.py` | `test_br_049` |
| VMS-BR-050 | Walk-in Contingency Approval SLA | `domain/validation.py` | `test_br_050` |
| VMS-BR-051 | Blacklist Registration Rejection | `domain/blacklist.py` | `test_br_051` |
| VMS-BR-052 | Host Approval Requirement | `domain/state_machine.py` | `test_br_052` |
| VMS-BR-053 | Walk-in Pass Duration | `domain/validation.py` | `test_br_053` |
| VMS-BR-062 | Pending Approval Timeout | `domain/validation.py` | `test_br_062` |
| VMS-BR-073 | Early Pass/Visit Termination Authorization | `domain/state_machine.py` | `test_br_073` |
| VMS-BR-077 | Active Pass Gate Rule | `domain/state_machine.py` | `test_br_077` |
| VMS-BR-082 | Gate Validation Failure Rule | `domain/validation.py` | `test_br_082` |
| VMS-BR-085 | Manual Gate Override Authorization | `domain/state_machine.py` | `test_br_085` |
| VMS-BR-096 | Temporary Zone Elevation Time Box | `domain/validation.py` | `test_br_096` |
| VMS-BR-101 | Automatic Checkout Trigger | `domain/state_machine.py` | `test_br_101` |
| VMS-BR-105 | Visit Completion Rule | `domain/state_machine.py` | `test_br_105` |
| VMS-BR-112 | Blacklist Runtime Checkpoints | `domain/blacklist.py` | `test_br_112` |
| VMS-BR-116 | Blacklist Entry Denial | `domain/blacklist.py` | `test_br_116` |
| VMS-BR-117 | Blacklist Match Alert | `domain/blacklist.py` | `test_br_117` |
| VMS-BR-118 | Temporary Safe-list Scope | `domain/blacklist.py` | `test_br_118` |
| VMS-BR-119 | Temporary Safe-list Expiry | `domain/blacklist.py` | `test_br_119` |
| VMS-BR-120 | Published Blacklist Runtime Source | `domain/blacklist.py` | `test_br_120` |
| VMS-BR-125 | Access Policy Versioning | `domain/validation.py` | `test_br_125` |
| VMS-BR-126 | Access Policy Publication | `domain/validation.py` | `test_br_126` |
| VMS-BR-127 | Published Access Policy Runtime Source | `domain/validation.py` | `test_br_127` |
| VMS-BR-128 | Policy Modification Creates New Version | `domain/validation.py` | `test_br_128` |
| VMS-BR-129 | Policy Non-retroactivity | `domain/validation.py` | `test_br_129` |
| VMS-BR-130 | Emergency Muster Trigger Authorization | `domain/state_machine.py` | `test_br_130` |
| VMS-BR-174 | Notification Channel Configuration | `domain/validation.py` | `test_br_174` |
| VMS-BR-181 | Time-bound VMS Role Assignment | `domain/validation.py` | `test_br_181` |
| VMS-BR-182 | Immediate Role Reassignment | `domain/validation.py` | `test_br_182` |
| VMS-BR-183 | Pending Work Handoff on Reassignment | `domain/state_machine.py` | `test_br_183` |
| VMS-BR-184 | VMS Role Hierarchy | `domain/state_machine.py` | `test_br_184` |
| VMS-BR-185 | Implicit Host Role | `domain/state_machine.py` | `test_br_185` |
| VMS-BR-186 | Valid Identity Document Requirement | `domain/validation.py` | `test_br_186` |
| VMS-BR-187 | Supported Identity Document Types | `domain/validation.py` | `test_br_187` |
| VMS-BR-190 | Pass Validity Window | `domain/validation.py` | `test_br_190` |
| VMS-BR-191 | Unauthorized Zone Access Denial | `domain/validation.py` | `test_br_191` |
| VMS-BR-192 | Unauthorized Zone Access Logging | `domain/validation.py` | `test_br_192` |
| VMS-BR-193 | Maximum Visit Duration | `domain/validation.py` | `test_br_193` |
| VMS-BR-194 | Extension Approval | `domain/state_machine.py` | `test_br_194` |
| VMS-BR-195 | Pre-authorization Approval Bypass | `domain/state_machine.py` | `test_br_195` |
| VMS-BR-196 | VIP Override Authorization | `domain/state_machine.py` | `test_br_196` |
| VMS-BR-197 | VIP Override Effect | `domain/state_machine.py` | `test_br_197` |
| VMS-BR-200 | Expired Request State | `domain/state_machine.py` | `test_br_200` |
| VMS-BR-202 | Advance Pre-registration Window | `domain/validation.py` | `test_br_202` |
| VMS-BR-203 | Same-day Urgent Visit Exception | `domain/state_machine.py` | `test_br_203` |
| VMS-BR-211 | Pass Type Domain | `domain/validation.py` | `test_br_211` |

---

## 3. Workflows (WF Mapping)

| Workflow ID | Workflow Name | Implementation Pathway | Test Suite |
|-------------|---------------|-------------------------|------------|
| BW-VMS-01 | Pre-registered Approved Visit | Pre-register -> Approve -> Gate In -> Gate Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_01` |
| BW-VMS-02 | Pre-registered Rejected Visit | Pre-register -> Host Reject | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_02` |
| BW-VMS-03 | Pre-registered Approval Timeout | Pre-register -> Expiry task | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_03` |
| BW-VMS-04 | Pre-authorized Visit | Host Pre-Auth -> Pre-register (Auto-Approve) -> In -> Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_04` |
| BW-VMS-05 | VIP Visit | Super Admin VIP flag -> Pre-register (Auto-Approve) -> In -> Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_05` |
| BW-VMS-06 | Walk-in Host-approved Visit | Gate Walk-in -> Host Approve -> In -> Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_06` |
| BW-VMS-07 | Walk-in Contingency-approved Visit | Gate Walk-in -> Host Timeout -> Admin Contingency -> In -> Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_07` |
| BW-VMS-08 | Walk-in Host-rejected Visit | Gate Walk-in -> Host Reject | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_08` |
| BW-VMS-09 | Gate Validation Denied | Pass Validation Failure at Gate | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_09` |
| BW-VMS-10 | Gate Denial with Authorized Override | Gate Denial -> Admin Manual Override -> In | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_10` |
| BW-VMS-11 | Offline Gate Entry and Reconciliation | Offline Scan -> Batch Reconcile | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_11` |
| BW-VMS-12 | Zone Access Granted | In -> Authorized Zone Scan | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_12` |
| BW-VMS-13 | Zone Access Denied and Alert Handled | In -> Unauthorized Zone Scan (Alert logged) | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_13` |
| BW-VMS-14 | Temporary Zone Elevation | In -> Admin Zone Elevation -> Zone Access | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_14` |
| BW-VMS-15 | Host Terminates Pass Before Check-in | Approved Pass -> Host Revoke | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_15` |
| BW-VMS-16 | Host Terminates On-site Visit | On-site Visit -> Host Terminate Early | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_16` |
| BW-VMS-17 | Admin Terminates Pass Before Check-in | Approved Pass -> Admin Revoke | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_17` |
| BW-VMS-18 | Admin Terminates On-site Visit | On-site Visit -> Admin Terminate Early | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_18` |
| BW-VMS-19 | Admin-triggered Emergency Muster | On-site Visits -> Admin Muster -> Roll Call | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_19` |
| BW-VMS-20 | Security-triggered Emergency Muster | On-site Visits -> Security Muster -> Roll Call | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_20` |
| BW-VMS-21 | Bulk Event Visitor Entry | Bulk Upload -> Batch In -> Batch Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_21` |
| BW-VMS-22 | Same-day Urgent Pre-registration | Same-day Urgent -> Admin Exception -> Approve -> In -> Out | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_22` |
| BW-VMS-23 | Admin-approved Visit Extension | On-site -> Extension Request -> Admin Approve | `modules/vms/tests/spec/wf/test_wf.py::test_wf_bw_23` |
| CW-VMS-01 | Pre-registered Visit Lifecycle | Composite of BW-01..05, 22 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_01` |
| CW-VMS-02 | Walk-in Visit Lifecycle | Composite of BW-06..08 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_02` |
| CW-VMS-03 | Gate Entry Validation & Exceptions | Composite of BW-09..11 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_03` |
| CW-VMS-04 | Zone Access and Elevation | Composite of BW-12..14 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_04` |
| CW-VMS-05 | Early Termination and Extension | Composite of BW-15..18, 23 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_05` |
| CW-VMS-06 | Emergency Muster and Accountability | Composite of BW-19..20 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_06` |
| CW-VMS-07 | Bulk Event Visitor Handling | Composite of BW-21 | `modules/vms/tests/spec/wf/test_wf.py::test_wf_cw_07` |
