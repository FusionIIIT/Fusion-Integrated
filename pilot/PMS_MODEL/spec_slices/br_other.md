# Other PMS business rules: access, audit, notifications, reports, deadlines (read-only spec)

- BR-PMS-005 (Reporting; applies to Director): Directors may access PMS reports and analytics only within their authorized PMS scope.
- BR-PMS-006 (Oversight; applies to Director): Director workflow-oversight access is limited to application workflows in the Director's domain.
- BR-PMS-088 (Request routing; applies to Applicant / Director): Licensing/technology-transfer requests are routed to the appropriate committee or Director according to the applicable institutional process.
- BR-PMS-091 (License records; applies to Director / PCC_ADMIN): License records are subject to confidentiality controls.
- BR-PMS-097 (Deadline tracking; applies to Director / PCC_ADMIN): PMS calculates/monitors the Director review deadline using the applicable review-deadline rule.
- BR-PMS-098 (Deadline tracking; applies to Applicant / Director): PMS calculates/monitors the revision deadline using the applicable revision-deadline rule.
- BR-PMS-099 (Deadline tracking; applies to Attorney / Applicant): PMS calculates/monitors office-action response deadlines only where applicable deadline rules/data are available. Exception: Applies only under the stated availability/configuration/legal condition. Outside the stated condition, the rule does not authorize the action.
- BR-PMS-101 (Deadline notification; applies to Relevant stakeholder): Where applicable, PMS generates an alert 30 days before a tracked deadline. Exception: Applies only under the stated availability/configuration/legal condition.
- BR-PMS-102 (Deadline notification; applies to Relevant stakeholder): Where applicable, PMS generates an alert 15 days before a tracked deadline. Exception: Applies only under the stated availability/configuration/legal condition.
- BR-PMS-103 (Deadline notification; applies to Relevant stakeholder): Where applicable, PMS generates an alert 5 days before a tracked deadline. Exception: Applies only under the stated availability/configuration/legal condition.
- BR-PMS-104 (Escalation; applies to PCC_ADMIN / relevant stakeholder): A missed tracked deadline triggers escalation according to the configured escalation chain.
- BR-PMS-116 (Scope boundary; applies to PMS / external email service): PMS responsibility for email notifications is limited to triggering system-generated emails; external delivery infrastructure is outside PMS.
- BR-PMS-121 (Audit log; applies to PCC_ADMIN / compliance reviewer): Where applicable, audit records include user ID, action type, timestamp, application ID, previous state, and new state. Exception: Applies only under the stated availability/configuration/legal condition.
- BR-PMS-122 (Audit log; applies to PCC_ADMIN / compliance reviewer): Critical PMS operations create immutable audit records.
- BR-PMS-131 (Role management; applies to PCC_ADMIN): PMS maintains exactly one active PCC_ADMIN oversight role.
- BR-PMS-139 (Scope boundary; applies to Financial systems): Financial systems and payment/accounting execution are external; PMS may record, validate, approve, track, log, or exchange financial metadata where integration is available. Exception: Applies only under the stated availability/configuration/legal condition.
