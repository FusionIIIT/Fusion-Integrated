# Gymkhana Use Case Specifications (v1.1 SYNCHRONIZED)

## UC-GYM-001 / Create New Club

- **UC Type**: Actor-triggered
- **Primary Actor**: Student Admin
- **Supporting Actors / Systems**: Shared user/student/faculty registry
- **Goal / Description**: Create a complete new club record with validated leadership and faculty-councillor assignments.
- **Trigger**: Student Admin chooses to create a new Gymkhana club.
- **Preconditions**: • Student Admin is authenticated and authorized. • Required student and faculty identity records are available.

### Flow of Events

#### Main Success Scenario
1. Student Admin enters the club name and description.
2. Student Admin selects an allowed club category.
3. Student Admin selects the coordinator and co-coordinator.
4. Student Admin selects the Club Faculty Councillor.
5. The system validates both student leaders and the faculty councillor.
6. The system creates the club with status open.
7. The system confirms successful creation.
#### Alternative Flows
If any selected leader/faculty record is invalid, the system identifies the invalid assignment and allows correction without creating the club.
#### Exception Flows
If required data cannot be stored, the club is not created and the system reports failure.

### Postconditions & Traceability

- **Success Postcondition**: A new club exists with open status.
- **Failure / Minimal Guarantee**: No partial club record is treated as a successfully created club.
- **Related Business Rules**: BR-GYM-001, BR-GYM-002, BR-GYM-003, BR-GYM-004
- **Related Workflow(s)**: BW-GYM-03
- **Notes / TODO**: Student Admin replaces the previous Academic Staff/Dean actor.

---

## UC-GYM-002 / Book Club Session

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: Notification service
- **Goal / Description**: Book a club session in a configured venue without creating a scheduling conflict.
- **Trigger**: Club Head initiates a session booking.
- **Preconditions**: • Actor is the applicable club coordinator/co-coordinator. • Club exists and is confirmed.

### Flow of Events

#### Main Success Scenario
1. The system identifies the actor's club.
2. Club Head selects a configured venue and date.
3. Club Head enters start time, end time, description, and optionally a poster.
4. The system validates the time range.
5. The system checks the requested slot against all existing sessions and events for the same venue/date.
6. The system creates the session when no conflict exists.
7. The system notifies the intended student recipients.
8. The system confirms the booking.
#### Alternative Flows
If the slot overlaps an existing session or event, the system rejects the booking and asks the actor to select another slot.
#### Exception Flows
If the venue is invalid, the time range is invalid, or storage/notification processing fails before acceptance, no successful booking is recorded.

### Postconditions & Traceability

- **Success Postcondition**: Session is stored and student notification is initiated.
- **Failure / Minimal Guarantee**: No conflicting or invalid session is accepted.
- **Related Business Rules**: BR-GYM-005, BR-GYM-006, BR-GYM-010, BR-GYM-020
- **Related Workflow(s)**: N/A
- **Notes / TODO**: Cross-type conflict checking is required even if the prior implementation checked session and event collections separately.

---

## UC-GYM-003 / Book Club Event

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: Notification service; faculty registry
- **Goal / Description**: Book a club event in a configured venue without creating a scheduling conflict.
- **Trigger**: Club Head initiates an event booking.
- **Preconditions**: • Actor is the applicable club coordinator/co-coordinator. • Club exists and is confirmed.

### Flow of Events

#### Main Success Scenario
1. The system identifies the actor's club.
2. Club Head enters the event name and identifies the Club Faculty Councillor/faculty context.
3. Club Head selects a configured venue and date.
4. Club Head enters start time, end time, poster, and description.
5. The system validates faculty context as applicable and validates the time range.
6. The system checks the requested slot against all existing sessions and events for the same venue/date.
7. The system creates the event when no conflict exists.
8. The system notifies the intended student recipients.
9. The system confirms the booking.
#### Alternative Flows
If the slot overlaps an existing session or event, the system rejects the booking and asks the actor to select another slot.
#### Exception Flows
If the venue, faculty reference, or time range is invalid, or the event cannot be stored, no successful event booking is recorded.

### Postconditions & Traceability

- **Success Postcondition**: Event is stored and student notification is initiated.
- **Failure / Minimal Guarantee**: No conflicting or invalid event is accepted.
- **Related Business Rules**: BR-GYM-002, BR-GYM-005, BR-GYM-006, BR-GYM-010, BR-GYM-020
- **Related Workflow(s)**: N/A
- **Notes / TODO**: None

---

## UC-GYM-004 / Apply for Club Membership

- **UC Type**: Actor-triggered
- **Primary Actor**: Student
- **Supporting Actors / Systems**: Shared user/student registry
- **Goal / Description**: Submit a membership application to a confirmed club.
- **Trigger**: Student chooses a club and applies for membership.
- **Preconditions**: • Student is authenticated. • Selected club exists and is confirmed.

### Flow of Events

#### Main Success Scenario
1. The system displays/selects available confirmed clubs.
2. Student selects a club.
3. Student enters achievements or application description.
4. The system identifies the authenticated student.
5. The system verifies that the student does not already have a duplicate application to the same club.
6. The system records the application with status open.
7. The system confirms submission.
#### Alternative Flows
The student may apply to another different club even when other applications exist.
#### Exception Flows
If a duplicate same-club application is detected, the system rejects the duplicate and leaves the existing application unchanged.

### Postconditions & Traceability

- **Success Postcondition**: A new open membership application exists for the selected club.
- **Failure / Minimal Guarantee**: No duplicate same-club application is created.
- **Related Business Rules**: BR-GYM-007, BR-GYM-008, BR-GYM-009
- **Related Workflow(s)**: BW-GYM-01
- **Notes / TODO**: None

---

## UC-GYM-005 / Approve Club Membership

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: Shared user/student registry
- **Goal / Description**: Approve one or more pending membership applications for the applicable club.
- **Trigger**: Club Head opens pending membership applications and chooses applications to approve.
- **Preconditions**: • Actor is the applicable club coordinator/co-coordinator. • One or more open applications exist for the club.

### Flow of Events

#### Main Success Scenario
1. The system displays pending applications for the actor's club.
2. Club Head selects an open application for approval.
3. Club Head may enter remarks.
4. The system validates the application and actor authorization.
5. The system changes the application status from open to confirmed and stores the remarks.
6. The system confirms successful approval.
#### Alternative Flows
Club Head may approve multiple selected pending applications in one interaction; each application is evaluated independently.
#### Exception Flows
If an application is no longer open or does not belong to the actor's club, it is not changed.

### Postconditions & Traceability

- **Success Postcondition**: Approved applications are confirmed.
- **Failure / Minimal Guarantee**: Unaffected applications retain their prior state.
- **Related Business Rules**: BR-GYM-010, BR-GYM-011
- **Related Workflow(s)**: BW-GYM-01
- **Notes / TODO**: Membership rejection/cancellation is outside the current baseline.

---

## UC-GYM-006 / Create Voting Poll

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: Notification service
- **Goal / Description**: Create a poll with choices, expiry, target audience, and notifications.
- **Trigger**: Club Head initiates poll creation.
- **Preconditions**: • Actor is the applicable club coordinator/co-coordinator.

### Flow of Events

#### Main Success Scenario
1. Club Head enters poll title and description.
2. Club Head provides an expiration date.
3. Club Head provides at least two choices.
4. Club Head selects target groups by batch and branch.
5. The system validates the poll definition and determines the target audience.
6. The system creates the poll and its choices.
7. The system notifies students in the selected target groups.
8. The system confirms poll creation.
#### Alternative Flows
A target branch selection may represent all branches for a selected batch where that option is configured.
#### Exception Flows
If fewer than two choices are supplied or target information is invalid, the poll is not created.

### Postconditions & Traceability

- **Success Postcondition**: An active poll with choices and target audience exists.
- **Failure / Minimal Guarantee**: No invalid poll is treated as successfully created.
- **Related Business Rules**: BR-GYM-010, BR-GYM-012, BR-GYM-013
- **Related Workflow(s)**: BW-GYM-02
- **Notes / TODO**: None

---

## UC-GYM-007 / Vote in Poll

- **UC Type**: Actor-triggered
- **Primary Actor**: Student
- **Supporting Actors / Systems**: None
- **Goal / Description**: View an eligible active poll and cast one vote.
- **Trigger**: Student selects an active poll available to the student.
- **Preconditions**: • Student is authenticated. • Poll is active/unexpired. • Student belongs to a target group for the poll. • Student has not already voted in the poll.

### Flow of Events

#### Main Success Scenario
1. The system presents the active poll and its choices.
2. Student selects one choice.
3. The system verifies poll eligibility and that the student has not already voted.
4. The system records the student's vote and updates the poll tally.
5. The system marks/records that the student has voted in the poll.
6. The system confirms successful voting.
#### Alternative Flows
None identified for the accepted baseline.
#### Exception Flows
If the student has already voted, is not eligible, or the poll is not active, the system rejects the vote and leaves the tally unchanged.

### Postconditions & Traceability

- **Success Postcondition**: One vote is recorded for the student in the poll.
- **Failure / Minimal Guarantee**: No duplicate or ineligible vote is added.
- **Related Business Rules**: BR-GYM-013, BR-GYM-014, BR-GYM-015
- **Related Workflow(s)**: BW-GYM-02
- **Notes / TODO**: None

---

## UC-GYM-008 / Change Club Leadership

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: Shared student registry / designation service
- **Goal / Description**: Replace the club coordinator and co-coordinator while keeping current leadership consistent.
- **Trigger**: Authorized Club Head initiates a leadership change.
- **Preconditions**: • Actor is an applicable current Club Head. • Club exists.

### Flow of Events

#### Main Success Scenario
1. Club Head identifies the club and the proposed new coordinator and co-coordinator.
2. The system validates both proposed leaders as students.
3. The system retrieves the current leadership assignments.
4. The system updates the club to the new coordinator and co-coordinator.
5. The system records the new current leadership designations.
6. The system removes/retires the superseded current leadership designations.
7. The system confirms the change.
#### Alternative Flows
None identified for the accepted baseline.
#### Exception Flows
If either proposed leader is invalid or the actor is unauthorized, the current leadership remains unchanged.

### Postconditions & Traceability

- **Success Postcondition**: The club references the new current coordinator and co-coordinator only.
- **Failure / Minimal Guarantee**: Existing leadership remains intact if the change fails.
- **Related Business Rules**: BR-GYM-001, BR-GYM-010, BR-GYM-016
- **Related Workflow(s)**: N/A
- **Notes / TODO**: None

---

## UC-GYM-009 / Request Club Budget

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: File storage
- **Goal / Description**: Submit and retain a club budget request for tracking.
- **Trigger**: Club Head initiates a budget request.
- **Preconditions**: • Actor is the applicable Club Head. • Club exists and is confirmed.

### Flow of Events

#### Main Success Scenario
1. Club Head enters the budget purpose.
2. Club Head enters a non-negative amount.
3. Club Head uploads the required supporting file.
4. Club Head enters a description.
5. The system validates amount and file presence.
6. The system stores the request with open status for tracking.
7. The system confirms successful submission.
#### Alternative Flows
None identified for the accepted baseline.
#### Exception Flows
If the amount is negative or the required file is missing, the request is rejected and not stored as a valid submission.

### Postconditions & Traceability

- **Success Postcondition**: An open club budget request exists for tracking.
- **Failure / Minimal Guarantee**: No invalid request is accepted.
- **Related Business Rules**: BR-GYM-010, BR-GYM-017, BR-GYM-018
- **Related Workflow(s)**: N/A
- **Notes / TODO**: Budget approval/rejection and all fest-budget functions are outside the current baseline.

---

## UC-GYM-010 / Submit Club Event Report

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Head
- **Supporting Actors / Systems**: Shared student registry; file storage
- **Goal / Description**: Submit a documented report for a completed club event.
- **Trigger**: Club Head chooses to record the event report.
- **Preconditions**: • Actor is the applicable Club Head. • Relevant event/activity has occurred.

### Flow of Events

#### Main Success Scenario
1. Club Head identifies the club and student incharge.
2. Club Head enters the event name and description.
3. Club Head enters the event date/time.
4. Club Head uploads the required report/details file.
5. The system validates the required information and file.
6. The system stores the event report.
7. The system confirms successful submission.
#### Alternative Flows
None identified for the accepted baseline.
#### Exception Flows
If the required report file or required references are invalid/missing, the report is not accepted.

### Postconditions & Traceability

- **Success Postcondition**: A submitted event report is available in the club repository.
- **Failure / Minimal Guarantee**: No incomplete report is treated as successfully submitted.
- **Related Business Rules**: BR-GYM-010, BR-GYM-019
- **Related Workflow(s)**: N/A
- **Notes / TODO**: None

---

## UC-GYM-011 / Approve Club

- **UC Type**: Actor-triggered
- **Primary Actor**: Student Admin
- **Supporting Actors / Systems**: None
- **Goal / Description**: Confirm an open club after Student Admin review.
- **Trigger**: Student Admin selects an open club for approval.
- **Preconditions**: • Student Admin is authenticated and authorized. • Club exists with open status.

### Flow of Events


### Postconditions & Traceability

- **Success Postcondition**: Club status is confirmed.
- **Failure / Minimal Guarantee**: Club retains its prior status if approval fails.
- **Related Business Rules**: BR-GYM-004
- **Related Workflow(s)**: BW-GYM-03
- **Notes / TODO**: A rejection transition is not specified in the current baseline.

---

## UC-GYM-012 / Review Club Event Report

- **UC Type**: Actor-triggered
- **Primary Actor**: Club Faculty Councillor
- **Supporting Actors / Systems**: File storage
- **Goal / Description**: Access and review event reports submitted for the councillor's assigned club.
- **Trigger**: Club Faculty Councillor opens the club report area.
- **Preconditions**: • Faculty user is authenticated. • User is the assigned Club Faculty Councillor for the club. • At least one submitted report is available.

### Flow of Events


### Postconditions & Traceability

- **Success Postcondition**: The councillor has reviewed/accessed the selected submitted report.
- **Failure / Minimal Guarantee**: No unauthorized report content is exposed.
- **Related Business Rules**: BR-GYM-021
- **Related Workflow(s)**: N/A
- **Notes / TODO**: Review is modeled as access/review only; no approval/rejection status is invented.

---
