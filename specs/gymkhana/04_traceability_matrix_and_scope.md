# Gymkhana Traceability Matrix & Scope Decisions

## Sheet: CFR Traceability

| Gymkhana Module - CFR Traceability |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RTM v1.1 | CFR roll-up |  |  |  |  |  |  |  |  |
| CFR ID | CFR Statement | Constituent AFRs | UC Coverage | BR Coverage | WF Coverage | Minimum Sufficient Representation | Coverage | Notes |
| CFR-GYM-001 | The system shall support Student Admin-controlled establishment of Gymkhana clubs by capturing the required club data, validating student leaders, the Club Faculty Councillor and the allowed category, creating the club in open status, and allowing Student Admin to confirm the open club. | AFR-GYM-001 to AFR-GYM-006 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |
| CFR-GYM-002 | The system shall allow an authorized Club Head to change the club coordinator and co-coordinator, validate replacement leaders as students, and ensure that only the new current leadership assignments remain active. | AFR-GYM-007 to AFR-GYM-009 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |
| CFR-GYM-003 | The system shall allow an authorized Club Head to book club sessions and events in configured venues, enforce valid time ranges and cross-type venue exclusivity, validate faculty context for events, and notify intended students after successful bookings. | AFR-GYM-010 to AFR-GYM-015 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |
| CFR-GYM-004 | The system shall support confirmed-club membership enrollment by allowing students to submit non-duplicate applications, retaining them as open, allowing the applicable Club Head to access and approve open applications with optional remarks, and recording approved memberships as confirmed. | AFR-GYM-016 to AFR-GYM-022 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |
| CFR-GYM-005 | The system shall support targeted club polling by allowing an authorized Club Head to create an active poll with an expiration date, at least two choices and batch/branch target groups, notifying the target audience, and allowing each eligible targeted student to cast at most one vote while recording the accepted tally. | AFR-GYM-023 to AFR-GYM-028 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |
| CFR-GYM-006 | The system shall allow an authorized Club Head to submit a non-negative club budget request with purpose, description and the required supporting file and store it as an open request for tracking, without an online approval/rejection lifecycle. | AFR-GYM-029 to AFR-GYM-031 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |
| CFR-GYM-007 | The system shall allow an authorized Club Head to submit a documented club event report and allow only the assigned Club Faculty Councillor to access and review submitted reports for that club, without creating an approval/rejection state. | AFR-GYM-032 to AFR-GYM-034 |  |  |  |  |  | Roll-up traceability; precise locations are recorded at AFR level. |


## Sheet: AFR Traceability

| Gymkhana Module - AFR Traceability |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RTM v1.1 | Precise AFR-level mapping to UC / BR / WF |  |  |  |  |  |  |  |  |  |
| AFR ID | Parent CFR | AFR Statement | PS Source | UC Coverage / Exact Location | BR Coverage | WF Coverage / STT Transition | Minimum Sufficient Representation | Coverage | Notes |
| AFR-GYM-001 | CFR-GYM-001 | The system shall allow Student Admin to create a new club by recording the club name, category, coordinator, co-coordinator, Club Faculty Councillor, and description. | PS 4.1; 5 |  |  |  |  |  | Club establishment now participates in BW-GYM-03. |
| AFR-GYM-002 | CFR-GYM-001 | The system shall validate that the selected club coordinator and co-coordinator are valid students before a club is created. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-003 | CFR-GYM-001 | The system shall validate that a selected Club Faculty Councillor is a valid faculty member. | PS 6 |  |  |  |  |  | AFR is reused by club creation and event booking; its parent remains the club-establishment CFR for historical one-to-one continuity. |
| AFR-GYM-004 | CFR-GYM-001 | The system shall restrict club category to Technical, Sports, or Cultural. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-005 | CFR-GYM-001 | The system shall record a newly created club in an open state pending Student Admin approval. | PS 4.1; 6 |  |  |  |  |  | Open club state is now explicitly represented in BW-GYM-03. |
| AFR-GYM-006 | CFR-GYM-001 | The system shall allow Student Admin to approve an open club and shall record the approved club as confirmed. | PS 4.1; 6 |  |  |  |  |  | Student Admin approval now completes BW-GYM-03. |
| AFR-GYM-007 | CFR-GYM-002 | The system shall allow the applicable Club Head to replace the club coordinator and co-coordinator assignments. | PS 4.1 |  |  |  |  |  |  |
| AFR-GYM-008 | CFR-GYM-002 | The system shall validate that newly assigned coordinator and co-coordinator users are valid students. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-009 | CFR-GYM-002 | When club leadership is changed, the system shall maintain only the current coordinator and co-coordinator leadership assignments for the club. | PS 3.1 |  |  |  |  |  |  |
| AFR-GYM-010 | CFR-GYM-003 | The system shall allow a Club Head to book a club session by providing a configured venue, date, start time, end time, description, and optional poster. | PS 4.1 |  |  |  |  |  | Isolated booking service; no connected workflow is specified. |
| AFR-GYM-011 | CFR-GYM-003 | The system shall accept a session or event booking only when its start time precedes its end time. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-012 | CFR-GYM-003 | The system shall prevent a session or event booking that overlaps any existing session or event in the same venue on the same date. | PS 3.2; 6 |  |  |  |  |  | Cross-type conflict semantics remain synchronized. |
| AFR-GYM-013 | CFR-GYM-003 | After a session is successfully booked, the system shall notify the intended student recipients of the new session. | PS 4.1 |  |  |  |  |  | Notification is represented within UC-GYM-002; no separate event-triggered UC is required. |
| AFR-GYM-014 | CFR-GYM-003 | The system shall allow a Club Head to book a club event by providing event details, Club Faculty Councillor information, configured venue, date, start time, end time, poster, and description. | PS 4.1 |  |  |  |  |  | Isolated booking service; no connected workflow is specified. |
| AFR-GYM-015 | CFR-GYM-003 | After an event is successfully booked, the system shall notify the intended student recipients of the new event. | PS 4.1 |  |  |  |  |  | Notification is represented within UC-GYM-003; no separate event-triggered UC is required. |
| AFR-GYM-016 | CFR-GYM-004 | The system shall allow a student to apply for membership in a confirmed club and provide an application description or achievements. | PS 4.1 |  |  |  |  |  |  |
| AFR-GYM-017 | CFR-GYM-004 | The system shall allow a student to maintain membership applications to multiple different clubs. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-018 | CFR-GYM-004 | The system shall prevent a student from submitting a duplicate membership application to the same club. | PS 3.3; 6 |  |  |  |  |  |  |
| AFR-GYM-019 | CFR-GYM-004 | The system shall record a newly submitted club-membership application with open status. | PS 3.3 |  |  |  |  |  |  |
| AFR-GYM-020 | CFR-GYM-004 | The system shall allow a Club Head to access the pending membership applications for the applicable club. | PS 3.3 |  |  |  |  |  |  |
| AFR-GYM-021 | CFR-GYM-004 | The system shall allow the applicable Club Head to approve an open membership application and optionally record remarks. | PS 4.1 |  |  |  |  |  |  |
| AFR-GYM-022 | CFR-GYM-004 | The system shall change an approved membership application from open to confirmed. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-023 | CFR-GYM-005 | The system shall allow a Club Head to create a voting poll with title, description, expiration date, choices, and target groups defined by batch and branch. | PS 4.1 |  |  |  |  |  |  |
| AFR-GYM-024 | CFR-GYM-005 | The system shall require at least two choices for a voting poll. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-025 | CFR-GYM-005 | When a voting poll is created, the system shall notify the students in its selected target groups. | PS 3.6; 4.1 |  |  |  |  |  | Notification remains part of poll creation; BR-GYM-013 governs target routing. |
| AFR-GYM-026 | CFR-GYM-005 | The system shall allow an eligible targeted student to access an active voting poll and its available choices. | PS 3.6 |  |  |  |  |  |  |
| AFR-GYM-027 | CFR-GYM-005 | The system shall allow an eligible targeted student to cast one choice in an active voting poll. | PS 3.6 |  |  |  |  |  |  |
| AFR-GYM-028 | CFR-GYM-005 | The system shall prevent more than one vote by the same student in the same poll and shall record the accepted vote in the poll tally. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-029 | CFR-GYM-006 | The system shall allow a Club Head to submit a club budget request with amount, purpose, description, and supporting file. | PS 4.1 |  |  |  |  |  |  |
| AFR-GYM-030 | CFR-GYM-006 | The system shall reject a club budget request whose amount is negative or whose required supporting file is missing. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-031 | CFR-GYM-006 | The system shall store a submitted club budget request as an open request for tracking; online approval or rejection is not part of the current baseline. | PS 3.4; 4.1-4.2 |  |  |  |  |  | Open request is submission/tracking only; online approval/rejection remains out of scope. |
| AFR-GYM-032 | CFR-GYM-007 | The system shall allow a Club Head to submit a club event report containing the club, student incharge, event name, event date/time, description, and report/details file. | PS 4.1 |  |  |  |  |  |  |
| AFR-GYM-033 | CFR-GYM-007 | The system shall require the report/details file when a club event report is submitted. | PS 6 |  |  |  |  |  |  |
| AFR-GYM-034 | CFR-GYM-007 | The system shall allow the assigned Club Faculty Councillor to access and review submitted event reports for the councillor's club. | PS 3.5; 4.1; 5 |  |  |  |  |  | Review/access is non-state-changing; no workflow is forced. |


## Sheet: UC-BR-WF CrossRef

| Gymkhana Module - UC / BR / WF Cross-Reference |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| RTM v1.1 | Reverse traceability and workflow eligibility |  |  |  |  |  |  |
| UC ID | Use Case Name | Related CFRs / AFRs | Related BRs | Related WFs | State-changing? | Workflow Eligibility / Rationale |
| UC-GYM-001 | Create New Club |  | BR-GYM-001 to BR-GYM-004 | BW-GYM-03 | Yes | Connected lifecycle with UC-GYM-011; same-actor progression is valid under DIRECT_FINAL_v2. |
| UC-GYM-002 | Book Club Session |  | BR-GYM-005, BR-GYM-006, BR-GYM-010, BR-GYM-020 | N/A | Yes | Isolated booking service; no additional state-changing UC progression is specified. |
| UC-GYM-003 | Book Club Event |  | BR-GYM-002, BR-GYM-005, BR-GYM-006, BR-GYM-010, BR-GYM-020 | N/A | Yes | Isolated booking service; AFR-GYM-003 faculty validation is reused. |
| UC-GYM-004 | Apply for Club Membership |  | BR-GYM-007 to BR-GYM-009 | BW-GYM-01 | Yes | First transition in membership enrollment. |
| UC-GYM-005 | Approve Club Membership |  | BR-GYM-010, BR-GYM-011 | BW-GYM-01 | Yes | Second transition in membership enrollment. |
| UC-GYM-006 | Create Voting Poll |  | BR-GYM-010, BR-GYM-012, BR-GYM-013 | BW-GYM-02 | Yes | First transition in targeted poll participation. |
| UC-GYM-007 | Vote in Poll |  | BR-GYM-013 to BR-GYM-015 | BW-GYM-02 | Yes | Second transition in targeted poll participation. |
| UC-GYM-008 | Change Club Leadership |  | BR-GYM-001, BR-GYM-010, BR-GYM-016 | N/A | Yes | Single isolated leadership-change service. |
| UC-GYM-009 | Request Club Budget |  | BR-GYM-010, BR-GYM-017, BR-GYM-018 | N/A | Yes | Single submission/tracking service; budget approval is out of scope. |
| UC-GYM-010 | Submit Club Event Report |  | BR-GYM-010, BR-GYM-019 | N/A | Yes | State-changing submission; follow-on UC-GYM-012 is non-state-changing. |
| UC-GYM-011 | Approve Club |  | BR-GYM-004 | BW-GYM-03 | Yes | Second transition in Student Admin club-establishment lifecycle. |
| UC-GYM-012 | Review Club Event Report |  | BR-GYM-021 | N/A | No | Information-access/review only; no persistent review-state transition is specified. |


## Sheet: Scope Decisions

| Decision Area | Final Synchronized Baseline |
| --- | --- |
| Club administration | Student Admin creates new clubs and approves open clubs to confirmed; the connected lifecycle is BW-GYM-03. |
| Membership | Apply + approve only. Rejection and cancellation are out of scope. |
| Venue conflicts | Cross-type exclusivity: session-session, event-event, and session-event overlap is prohibited. |
| Budget | Club budget request submission/tracking retained. Online approval/rejection and fest budgets are out of scope. |
| Fest/core-team/forms/file tracking | Out of current Gymkhana baseline. |
| Event report review | Assigned Club Faculty Councillor may access/review submitted reports; no approval/rejection state is specified. |

