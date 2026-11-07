# PMS application state transitions (authoritative table, merged from all 16 basis workflows; read-only spec)

| From state | Actor | Use case | Guard / outcome | Resulting state |
|---|---|---|---|---|

| Draft / Not Submitted | Applicant | UC-PMS-001 / Submit Patent Application | Submission passes completeness/document validation | Submitted |
| Submitted | PCC_ADMIN | UC-PMS-007 / Assign Application to Director | Eligible Director selected or valid automatic routing succeeds | Under Review |
| Under Review | Director | UC-PMS-008 / Review Patent Application | Decision = Approve; justification >=50 characters; review within deadline | Approved |
| Under Review | Director | UC-PMS-008 / Review Patent Application | Decision = Needs Revision; valid justification | Needs Revision |
| Needs Revision | Applicant | UC-PMS-005 / Revise and Resubmit Application | Within 60 days; revision addresses feedback | Resubmitted |
| Resubmitted | PCC_ADMIN | UC-PMS-007 / Assign Application to Director | Valid assignment/reassignment | Under Review |
| Under Review | Director | UC-PMS-008 / Review Patent Application | Decision = Reject; valid justification | Rejected |
| Rejected | Applicant | UC-PMS-022 / File Appeal Against Rejection | Appeal filed within allowed period with grounds/justification | Appeal Submitted |
| Appeal Submitted | Director | UC-PMS-023 / Review Appeal | Appeal outcome = Remand for Amendment | Remanded for Amendment |
| Appeal Submitted | Director | UC-PMS-023 / Review Appeal | Appeal outcome = Uphold Rejection | Rejection Upheld |
| Appeal Submitted | Director | UC-PMS-023 / Review Appeal | Appeal outcome = Modify Decision | Decision Modified |
| Approved | PCC_ADMIN | UC-PMS-010 / Assign Attorney to Approved Application | Assignment satisfies panel/expertise/workload/conflict/preference rules | Assignment Offered |
| Assignment Offered | Attorney | UC-PMS-011 / Accept or Decline Attorney Assignment | Outcome = Accept | Attorney Assigned |
| Assignment Offered | Attorney | UC-PMS-011 / Accept or Decline Attorney Assignment | Outcome = Decline | Pending Review |
| Pending Review | PCC_ADMIN | UC-PMS-010 / Assign Attorney to Approved Application | Valid reassignment to another eligible Attorney | Assignment Offered |
| Approved | Director | UC-PMS-009 / Review and Decide Patent Budget | Cost within applicable threshold; budget availability validated where data exists; outcome = Approve | Budget Approved |
| Approved | Director | UC-PMS-009 / Review and Decide Patent Budget | Outcome = Reject | Budget Rejected |
| Approved | Director | UC-PMS-009 / Review and Decide Patent Budget | Total cost exceeds configured threshold | Escalated |
| Escalated | PCC_ADMIN | UC-PMS-027 / Monitor Workflow and Handle Exceptional Cases | Handle/route the exceptional case within PMS scope | Escalation Tracked / External Decision Pending |
| Pre-Filing Preconditions Satisfied | Attorney | UC-PMS-013 / Prepare and Record External Patent Filing | Required approvals and budget complete; inventor agreements complete; applicable format rules satisfied; international justification if needed | Filed |
| Filed / Post-Filing Active | Attorney | UC-PMS-014 / Record Patent Office Communication | Official communication is an office action | Office Action Recorded |
| Office Action Recorded | Attorney | UC-PMS-015 / Respond to Office Action | Applicant review is required; draft prepared | Awaiting Applicant Approval |
| Awaiting Applicant Approval | Applicant | UC-PMS-029 / Review Office-Action Response | Applicant records approval | Applicant Approved |
| Applicant Approved | Attorney | UC-PMS-015 / Respond to Office Action | Response finalized and recorded submitted within deadline or permitted extension | Response Submitted |
| Office Action Recorded | Attorney | UC-PMS-015 / Respond to Office Action | Applicant review not required; draft finalized | Response Ready |
| Response Ready | Attorney | UC-PMS-015 / Respond to Office Action | Response recorded submitted within deadline or permitted extension | Response Submitted |
| Granted / Maintenance Cycle Active | Attorney | UC-PMS-017 / Manage Post-Grant Tracking and Maintenance | Maintenance decision is due | Renewal Decision Requested |
| Renewal Decision Requested | Director | UC-PMS-018 / Make Maintenance Renewal Decision | Outcome = Renew | Renewal Approved |
| Renewal Approved | Attorney | UC-PMS-017 / Manage Post-Grant Tracking and Maintenance | Maintenance action recorded; next cycle scheduled | Renewed / Next Cycle Scheduled |
| Renewal Decision Requested | Director | UC-PMS-018 / Make Maintenance Renewal Decision | Outcome = Do Not Renew | Do Not Renew |
| Any configured withdrawal-eligible pre-filing state | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing; current status is withdrawal-eligible; reason provided; co-inventor consent if required | Withdrawn |
| Under Review | Director | UC-PMS-008 / Review Patent Application | Needs Revision | BR-PMS-029; BR-PMS-030; BR-PMS-031 |
| Renewal Decision Requested | Director | UC-PMS-018 / Make Maintenance Renewal Decision | Do Not Renew | BR-PMS-061 |
| Submitted | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
| Under Review | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
| Needs Revision | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
| Rejected | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
| Approved | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
| Attorney Assigned | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
| Pending Review | Applicant | UC-PMS-006 / Withdraw Patent Application | Before filing AND current state is configured/defined as withdrawal-eligible | Withdrawn |
