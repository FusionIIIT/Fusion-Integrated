---
title: SPACS Domain Model
module: spacs
module_name: Other Academic Procedures (OAP) - Awards and Scholarships (SPACS)
status: approved
author: Sunkara Nandan (24BCS246)
reviewer: Pulkit Sharma (24BEC099)
last_reviewed: 2026-11-20
---

# SPACS Domain Model

## 1. Overview
The Awards and Scholarships (`spacs`) module manages institute-administered financial aid opportunities, merit scholarships, and convocation awards within Fusion ERP. It provides digital workflows for catalog publishing, policy-driven application submission, evidence verification, committee evaluation, Senate/Director approval tracking, and immutable audit logging.

## 2. Core Aggregates and Entities

```mermaid
classDiagram
    class SchemeCatalogue {
        +UUID id
        +String code
        +String name
        +String scheme_type
        +Boolean is_active
        +Boolean allows_renewal
    }
    class SchemePolicyVersion {
        +UUID id
        +String version_tag
        +Decimal min_cpi
        +Decimal max_income
        +String status
        +DateTime deadline
    }
    class ScholarshipApplication {
        +UUID id
        +String application_number
        +String student_user_id
        +String academic_cycle
        +String status
        +JSON facts
        +JSON eligibility_snapshot
    }
    class ApplicationDocument {
        +UUID id
        +String doc_type
        +String file_key
        +String verification_status
    }
    class AwardCandidate {
        +UUID id
        +String student_user_id
        +Decimal score
        +String status
    }
    class AwardAllocation {
        +UUID id
        +String status
        +String approval_reference
    }
    class SpacsAuditLog {
        +UUID id
        +String actor_user_id
        +String action
        +DateTime timestamp
    }
    class SpacsNotification {
        +UUID id
        +String recipient_user_id
        +String notification_type
        +Boolean is_read
    }

    SchemeCatalogue "1" *-- "many" SchemePolicyVersion
    SchemeCatalogue "1" *-- "many" ScholarshipApplication
    ScholarshipApplication "1" *-- "many" ApplicationDocument
    SchemeCatalogue "1" *-- "many" AwardCandidate
    AwardCandidate "1" *-- "1" AwardAllocation
    ScholarshipApplication "1" *-- "many" SpacsAuditLog
```

### 2.1 SchemeCatalogue & SchemePolicyVersion
- **SchemeCatalogue**: The root definition of an institutional scholarship or award opportunity (e.g. Merit-cum-Means, Director's Gold Medal, Convocation Proficiency Prize).
- **SchemePolicyVersion**: Immutable versioned parameters governing eligibility criteria, financial ceilings, evaluation weightages, and submission windows. Changes to scheme rules require issuing a new policy version without altering past application baselines.

### 2.2 ScholarshipApplication & ApplicationDocument
- **ScholarshipApplication**: Represents a student's submission for a scholarship in a given academic cycle. Contains applicant declarations (`facts`), system evaluation results (`eligibility_snapshot`), and lifecycle status.
- **ApplicationDocument**: Uploaded certified evidence (income certificate, caste certificate, grade card) linked to an application, subject to assistant verification and cryptographic storage key references.

### 2.3 AwardCandidate & AwardAllocation
- **AwardCandidate**: Candidates nominated for competitive convocation medals and awards. Supports multi-member committee scoring and ranking.
- **AwardAllocation**: Final allocation record requiring Senate or Board approval reference before public dissemination.

### 2.4 Audit & Notifications
- **SpacsAuditLog**: Append-only compliance log capturing actor ID, event type, prior state, new state, and timestamp for all lifecycle transitions.
- **SpacsNotification**: Multi-channel outbox recording messages sent to students, assistants, conveners, and committee members.
