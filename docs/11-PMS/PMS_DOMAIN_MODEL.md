# PMS Domain Model (as implemented)

This is a description of the current code, not an approved blueprint and not a replacement for the six PMS specifications. Source: `modules/pms/models.py`.

## Application aggregate

`PatentApplication` stores application content, the lifecycle status, domain/jurisdiction, applicant and assigned actor IDs, filing/grant metadata, and review/revision deadlines. Actor IDs are plain integers from IAM; PMS does not use cross-module foreign keys.

Application-owned records use foreign keys to `PatentApplication`:

| Model | Purpose and relationship |
| --- | --- |
| `CoInventor` | Inventor identity, ownership, agreement, consent, and signature state. |
| `ApplicationDocument` | Document metadata, version/current flags, sensitivity, file URL, and malware scan flags. A binary file store/scanner is not integrated. |
| `DirectorReview` | Director decision and justification history. |
| `PatentBudget` | One-to-one budget components and decision metadata. |
| `AttorneyAssignment` | Attorney assignment offer/response state and activity. |
| `PatentabilityAssessment` | Attorney assessment and recommendation. |
| `PriorArtReference` | Attached external reference metadata. |
| `OfficeAction` | Official communication and response workflow state. |
| `PostGrantMaintenance` | Maintenance cycle, decision, and action record. |
| `LicensingRequest` | Licensing/technology-transfer request and negotiation state. |
| `PatentAppeal` | Applicant grounds/justification and Director appeal outcome. |
| `PatentLegalAdvice` | Attorney-authored advice notes. |

## Cross-cutting records

- `PmsAuditTrail` stores actor/action/time, optional application, state values, and details.
- `PmsNotificationOutbox` stores idempotent notification events for delivery.
- `PmsConfiguration` stores validated policy overrides and descriptions.
- `AttorneyPanel` stores PMS attorney eligibility, expertise, and workload metadata.
- `PmsRoleAssignment` currently stores role and Director-domain assignments inside PMS. This duplicates access-control/designation data owned by IAM and remains an unresolved architecture finding; it must not be treated as an approved design.

The document flags `malware_scanned` and `is_clean` now default false. Application services refuse document acceptance when no trusted scanner result is available. Existing records are marked unverified by migration `0004_fail_closed_document_scan_defaults.py`.
