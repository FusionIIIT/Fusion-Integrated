---
title: SPACS Eligibility Evaluation Rules
module: spacs
status: approved
author: Sunkara Nandan (24BCS246)
reviewer: Pulkit Sharma (24BEC099)
last_reviewed: 2026-11-20
---

# Eligibility Evaluation Specification

## 1. Core Rule Engine
1. **BR-SPACS-001 (Academic Performance)**:
   - Criterion: `student_cpi >= policy.min_cpi`.
   - Evaluation is inclusive at threshold boundary.
2. **BR-SPACS-001 (Financial Need)**:
   - Criterion: `annual_family_income <= policy.max_income`.
   - Inclusive ceiling check supported by valid income certificate.
3. **BR-SPACS-004 (Document Expiry)**:
   - Attached income and caste certificates must have `valid_until >= application_date`.
4. **BR-SPACS-018 (Renewal Submission Window)**:
   - Renewal requests must be submitted before `policy.renewal_window_end`.
5. **BR-SPACS-020 (Disciplinary Clearance Gate)**:
   - Students with active disciplinary sanctions or academic probations are ineligible for award allocation.
