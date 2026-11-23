# Department: where each spec id is enforced

Written by `ops/docs/department_reference.py`; do not edit by hand.

| Id | Enforced at | What |
|---|---|---|
| BR-DEPT-001 | [modules/department/registry.py:87](../../modules/department/registry.py#L87) | creation permission granted only to Faculty, Dept_Admin, HOD |
| BR-DEPT-002 | [modules/department/selectors/scoping.py:51](../../modules/department/selectors/scoping.py#L51) | relevance filter by role, programme, year |
| BR-DEPT-003 | [modules/department/domain/rules.py:23](../../modules/department/domain/rules.py#L23) | content and target completeness |
| BR-DEPT-004 | [modules/department/domain/state_machine.py:81](../../modules/department/domain/state_machine.py#L81) | edit, hide, delete: HOD only, by acting role |
| BR-DEPT-005 | [modules/department/domain/state_machine.py:44](../../modules/department/domain/state_machine.py#L44) | only Faculty may create a request |
| BR-DEPT-006 | [modules/department/domain/state_machine.py:45](../../modules/department/domain/state_machine.py#L45) | only the HOD decides |
| BR-DEPT-007 | [modules/department/domain/state_machine.py:48](../../modules/department/domain/state_machine.py#L48) | issue only from approved, by Dept_Admin |
| BR-DEPT-008 | [modules/department/domain/state_machine.py:53](../../modules/department/domain/state_machine.py#L53) | only Students and Faculty submit |
| BR-DEPT-009 | [modules/department/domain/state_machine.py:58](../../modules/department/domain/state_machine.py#L58) | terminal disposition by Dept_Admin or HOD |
| BR-DEPT-010 | [modules/department/domain/rules.py:115](../../modules/department/domain/rules.py#L115) | overlapping slots refused |
| BR-DEPT-011 | [modules/department/services/departments.py:38](../../modules/department/services/departments.py#L38) | official change stays pending |
| BR-DEPT-012 | [modules/department/selectors/scoping.py:75](../../modules/department/selectors/scoping.py#L75) | Faculty resource scope |
| BR-DEPT-013 | [modules/department/services/departments.py:62](../../modules/department/services/departments.py#L62) | HOD decides official changes |
| BR-DEPT-015 | [modules/department/domain/rules.py:65](../../modules/department/domain/rules.py#L65) | request-time availability |
| BR-DEPT-016 | [modules/department/models/inventory.py:38](../../modules/department/models/inventory.py#L38) | append-only movement log |
| BR-DEPT-017 | [modules/department/selectors/scoping.py:85](../../modules/department/selectors/scoping.py#L85) | confidential feedback scope |
| BR-DEPT-018 | [modules/department/domain/state_machine.py:55](../../modules/department/domain/state_machine.py#L55) | Dept_Admin initial review first |
| BR-DEPT-019 | [modules/department/domain/rules.py:211](../../modules/department/domain/rules.py#L211) | profile visibility matrix |
| BR-DEPT-021 | [modules/department/services/roles.py:93](../../modules/department/services/roles.py#L93) | central authority records tenures |
| BR-DEPT-022 | [modules/department/domain/rules.py:182](../../modules/department/domain/rules.py#L182) | never two holders at once |
| BR-DEPT-023 | [modules/department/models/roles.py:27](../../modules/department/models/roles.py#L27) | validity interval required |
| BR-DEPT-024 | [modules/department/selectors/actors.py:20](../../modules/department/selectors/actors.py#L20) | access follows the tenure in effect now |
| UC-DEPT-001 | [modules/department/api/views.py:234](../../modules/department/api/views.py#L234) | view relevant announcements |
| UC-DEPT-002 | [modules/department/services/announcements.py:18](../../modules/department/services/announcements.py#L18) | create and publish |
| UC-DEPT-003 | [modules/department/services/announcements.py:74](../../modules/department/services/announcements.py#L74) | edit, hide, delete |
| UC-DEPT-004 | [modules/department/services/inventory.py:66](../../modules/department/services/inventory.py#L66) | request stock |
| UC-DEPT-005 | [modules/department/services/inventory.py:102](../../modules/department/services/inventory.py#L102) | approve or reject |
| UC-DEPT-006 | [modules/department/services/inventory.py:127](../../modules/department/services/inventory.py#L127) | issue stock |
| UC-DEPT-007 | [modules/department/services/feedback.py:27](../../modules/department/services/feedback.py#L27) | submit feedback |
| UC-DEPT-008 | [modules/department/services/feedback.py:69](../../modules/department/services/feedback.py#L69) | initial review and disposition |
| UC-DEPT-009 | [modules/department/services/resources.py:66](../../modules/department/services/resources.py#L66) | manage timetable |
| UC-DEPT-010 | [modules/department/services/departments.py:23](../../modules/department/services/departments.py#L23) | update details |
| UC-DEPT-011 | [modules/department/selectors/scoping.py:107](../../modules/department/selectors/scoping.py#L107) | view department resources |
| UC-DEPT-012 | [modules/department/services/departments.py:62](../../modules/department/services/departments.py#L62) | approve official changes |
| UC-DEPT-014 | [modules/department/services/feedback.py:108](../../modules/department/services/feedback.py#L108) | HOD oversight |
| UC-DEPT-015 | [modules/department/selectors/profiles.py:35](../../modules/department/selectors/profiles.py#L35) | view profiles at tier |
| UC-DEPT-016 | [modules/department/services/resources.py:126](../../modules/department/services/resources.py#L126) | manage profiles |
| UC-DEPT-017 | [modules/department/services/resources.py:103](../../modules/department/services/resources.py#L103) | manage lab profiles |
| UC-DEPT-018 | [modules/department/selectors/scoping.py:97](../../modules/department/selectors/scoping.py#L97) | student timetable and programme view |
| UC-DEPT-019 | [modules/department/services/inventory.py:25](../../modules/department/services/inventory.py#L25) | manage inventory records |
| UC-DEPT-020 | [modules/department/services/roles.py:93](../../modules/department/services/roles.py#L93) | maintain role assignments |
| UC-DEPT-022 | [modules/department/services/roles.py:163](../../modules/department/services/roles.py#L163) | apply effective transition |
| BW-DEPT-01 | [modules/department/domain/state_machine.py:43](../../modules/department/domain/state_machine.py#L43) | approved and issued path |
| BW-DEPT-02 | [modules/department/domain/state_machine.py:46](../../modules/department/domain/state_machine.py#L46) | rejected path |
| BW-DEPT-03 | [modules/department/domain/state_machine.py:52](../../modules/department/domain/state_machine.py#L52) | Dept_Admin disposition path |
| BW-DEPT-04 | [modules/department/domain/state_machine.py:52](../../modules/department/domain/state_machine.py#L52) | HOD oversight path |
| BW-DEPT-05 | [modules/department/domain/state_machine.py:74](../../modules/department/domain/state_machine.py#L74) | approved official change |
| BW-DEPT-06 | [modules/department/domain/state_machine.py:77](../../modules/department/domain/state_machine.py#L77) | rejected official change |
| BW-DEPT-07 | [modules/department/services/roles.py:72](../../modules/department/services/roles.py#L72) | HOD reassignment closes the outgoing tenure |
| BW-DEPT-08 | [modules/department/services/roles.py:72](../../modules/department/services/roles.py#L72) | Dept_Admin reassignment closes the outgoing tenure |
| CW-DEPT-01 | [modules/department/domain/state_machine.py:43](../../modules/department/domain/state_machine.py#L43) | stock lifecycle table |
| CW-DEPT-02 | [modules/department/domain/state_machine.py:52](../../modules/department/domain/state_machine.py#L52) | feedback lifecycle table |
| CW-DEPT-03 | [modules/department/domain/state_machine.py:71](../../modules/department/domain/state_machine.py#L71) | official change lifecycle table |
| CW-DEPT-04 | [modules/department/services/roles.py:163](../../modules/department/services/roles.py#L163) | reassignment lifecycle takes effect |
| CFR-DEPT-001 | [modules/department/services/announcements.py:18](../../modules/department/services/announcements.py#L18) | publish and notify |
| CFR-DEPT-002 | [modules/department/selectors/scoping.py:51](../../modules/department/selectors/scoping.py#L51) | relevant announcements |
| CFR-DEPT-003 | [modules/department/services/announcements.py:65](../../modules/department/services/announcements.py#L65) | HOD maintains active announcements, through the table |
| CFR-DEPT-004 | [modules/department/services/inventory.py:56](../../modules/department/services/inventory.py#L56) | inventory and insertion audit |
| CFR-DEPT-005 | [modules/department/services/inventory.py:127](../../modules/department/services/inventory.py#L127) | request to final outcome |
| CFR-DEPT-006 | [modules/department/selectors/scoping.py:75](../../modules/department/selectors/scoping.py#L75) | Faculty issued-stock history |
| CFR-DEPT-007 | [modules/department/services/feedback.py:27](../../modules/department/services/feedback.py#L27) | confidential feedback |
| CFR-DEPT-008 | [modules/department/services/feedback.py:95](../../modules/department/services/feedback.py#L95) | review and resolve |
| CFR-DEPT-009 | [modules/department/services/resources.py:172](../../modules/department/services/resources.py#L172) | manage profiles |
| CFR-DEPT-010 | [modules/department/domain/rules.py:222](../../modules/department/domain/rules.py#L222) | profile visibility |
| CFR-DEPT-011 | [modules/department/services/resources.py:51](../../modules/department/services/resources.py#L51) | conflict-free timetables |
| CFR-DEPT-012 | [modules/department/services/resources.py:103](../../modules/department/services/resources.py#L103) | lab resource profiles |
| CFR-DEPT-013 | [modules/department/selectors/scoping.py:97](../../modules/department/selectors/scoping.py#L97) | student academic information |
| CFR-DEPT-014 | [modules/department/domain/rules.py:147](../../modules/department/domain/rules.py#L147) | general information only |
| CFR-DEPT-015 | [modules/department/domain/rules.py:132](../../modules/department/domain/rules.py#L132) | official changes controlled |
| CFR-DEPT-016 | [modules/department/services/roles.py:124](../../modules/department/services/roles.py#L124) | role assignments and effective access |
| AFR-DEPT-001 | [modules/department/services/announcements.py:18](../../modules/department/services/announcements.py#L18) | create and publish |
| AFR-DEPT-002 | [modules/department/selectors/scoping.py:58](../../modules/department/selectors/scoping.py#L58) | role, programme, year filter |
| AFR-DEPT-003 | [modules/department/api/views.py:234](../../modules/department/api/views.py#L234) | authenticated users view |
| AFR-DEPT-004 | [modules/department/services/announcements.py:74](../../modules/department/services/announcements.py#L74) | HOD edit |
| AFR-DEPT-005 | [modules/department/services/announcements.py:91](../../modules/department/services/announcements.py#L91) | HOD hide |
| AFR-DEPT-006 | [modules/department/services/announcements.py:100](../../modules/department/services/announcements.py#L100) | HOD delete (soft, Q7) |
| AFR-DEPT-007 | [modules/department/services/inventory.py:25](../../modules/department/services/inventory.py#L25) | insert stock |
| AFR-DEPT-008 | [modules/department/services/inventory.py:56](../../modules/department/services/inventory.py#L56) | current quantity from the ledger |
| AFR-DEPT-009 | [modules/department/services/inventory.py:66](../../modules/department/services/inventory.py#L66) | Faculty request |
| AFR-DEPT-010 | [modules/department/domain/rules.py:65](../../modules/department/domain/rules.py#L65) | quantity validated |
| AFR-DEPT-011 | [modules/department/services/inventory.py:102](../../modules/department/services/inventory.py#L102) | HOD approve or reject |
| AFR-DEPT-012 | [modules/department/domain/state_machine.py:48](../../modules/department/domain/state_machine.py#L48) | issue only approved |
| AFR-DEPT-013 | [modules/department/services/inventory.py:140](../../modules/department/services/inventory.py#L140) | decrement on issue |
| AFR-DEPT-014 | [modules/department/services/inventory.py:58](../../modules/department/services/inventory.py#L58) | insertion logged |
| AFR-DEPT-015 | [modules/department/services/inventory.py:144](../../modules/department/services/inventory.py#L144) | issuance logged |
| AFR-DEPT-016 | [modules/department/selectors/scoping.py:75](../../modules/department/selectors/scoping.py#L75) | Faculty issued history (Q12) |
| AFR-DEPT-017 | [modules/department/services/feedback.py:27](../../modules/department/services/feedback.py#L27) | Students and Faculty submit |
| AFR-DEPT-018 | [modules/department/selectors/scoping.py:85](../../modules/department/selectors/scoping.py#L85) | confidential scope |
| AFR-DEPT-019 | [modules/department/services/feedback.py:69](../../modules/department/services/feedback.py#L69) | Dept_Admin initial review |
| AFR-DEPT-020 | [modules/department/domain/rules.py:160](../../modules/department/domain/rules.py#L160) | optional category (Q11) |
| AFR-DEPT-021 | [modules/department/services/feedback.py:88](../../modules/department/services/feedback.py#L88) | close a simple issue during review |
| AFR-DEPT-022 | [modules/department/services/feedback.py:54](../../modules/department/services/feedback.py#L54) | Resolved or Closed |
| AFR-DEPT-023 | [modules/department/selectors/scoping.py:93](../../modules/department/selectors/scoping.py#L93) | HOD sees feedback after initial review |
| AFR-DEPT-024 | [modules/department/services/resources.py:126](../../modules/department/services/resources.py#L126) | manage profile records |
| AFR-DEPT-025 | [modules/department/domain/rules.py:217](../../modules/department/domain/rules.py#L217) | Students: basic |
| AFR-DEPT-026 | [modules/department/domain/rules.py:216](../../modules/department/domain/rules.py#L216) | Faculty on students: basic until rosters exist (Q2) |
| AFR-DEPT-027 | [modules/department/domain/rules.py:216](../../modules/department/domain/rules.py#L216) | Faculty on Faculty/Alumni: limited |
| AFR-DEPT-028 | [modules/department/domain/rules.py:213](../../modules/department/domain/rules.py#L213) | HOD/Dept_Admin: full, no sensitive fields |
| AFR-DEPT-029 | [modules/department/services/resources.py:66](../../modules/department/services/resources.py#L66) | upload |
| AFR-DEPT-030 | [modules/department/services/resources.py:82](../../modules/department/services/resources.py#L82) | modify |
| AFR-DEPT-031 | [modules/department/services/resources.py:51](../../modules/department/services/resources.py#L51) | detect and block overlaps |
| AFR-DEPT-034 | [modules/department/services/resources.py:103](../../modules/department/services/resources.py#L103) | update lab details |
| AFR-DEPT-035 | [modules/department/selectors/scoping.py:107](../../modules/department/selectors/scoping.py#L107) | Faculty view labs |
| AFR-DEPT-036 | [modules/department/api/views.py:93](../../modules/department/api/views.py#L93) | programme information (Q9) |
| AFR-DEPT-037 | [modules/department/selectors/scoping.py:97](../../modules/department/selectors/scoping.py#L97) | applicable timetable |
| AFR-DEPT-038 | [modules/department/services/departments.py:23](../../modules/department/services/departments.py#L23) | general information |
| AFR-DEPT-039 | [modules/department/services/departments.py:38](../../modules/department/services/departments.py#L38) | pending until HOD approval |
| AFR-DEPT-040 | [modules/department/services/departments.py:62](../../modules/department/services/departments.py#L62) | HOD approve or reject |
| AFR-DEPT-041 | [modules/department/services/inventory.py:85](../../modules/department/services/inventory.py#L85) | notify Dept_Admin of a new request |
| AFR-DEPT-042 | [modules/department/services/inventory.py:92](../../modules/department/services/inventory.py#L92) | notify HOD |
| AFR-DEPT-043 | [modules/department/services/inventory.py:152](../../modules/department/services/inventory.py#L152) | notify Faculty on Issued (and on Rejected in decide) |
| AFR-DEPT-044 | [modules/department/services/feedback.py:45](../../modules/department/services/feedback.py#L45) | notify Dept_Admin of new feedback |
| AFR-DEPT-045 | [modules/department/services/feedback.py:60](../../modules/department/services/feedback.py#L60) | notify the submitter |
| AFR-DEPT-046 | [modules/department/services/notifications.py:76](../../modules/department/services/notifications.py#L76) | notify the announcement's audience |
| AFR-DEPT-047 | [modules/department/services/roles.py:37](../../modules/department/services/roles.py#L37) | assign to institute employees |
| AFR-DEPT-048 | [modules/department/models/roles.py:19](../../modules/department/models/roles.py#L19) | time-bounded validity |
| AFR-DEPT-049 | [modules/department/selectors/actors.py:28](../../modules/department/selectors/actors.py#L28) | outgoing access ends at valid_to |
| AFR-DEPT-050 | [modules/department/selectors/actors.py:27](../../modules/department/selectors/actors.py#L27) | incoming access starts at valid_from |
| AFR-DEPT-051 | [modules/department/services/roles.py:88](../../modules/department/services/roles.py#L88) | one HOD in effect |
| AFR-DEPT-052 | [modules/department/services/roles.py:88](../../modules/department/services/roles.py#L88) | one Dept_Admin in effect |
| AFR-DEPT-053 | [modules/department/selectors/profiles.py:47](../../modules/department/selectors/profiles.py#L47) | headship derived from the HOD tenure |
