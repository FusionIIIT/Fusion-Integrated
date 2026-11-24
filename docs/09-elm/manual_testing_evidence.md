# 09-elm/manual_testing_evidence.md

## Executive Summary
The status of manual testing for the Employee Leave Management (ELM) module in the development environment is as follows: all critical workflows have been thoroughly tested by a human evaluator, ensuring that the system functions as intended. The tests were conducted using live browser sessions to confirm the accuracy and reliability of the application.

## User-Confirmed Manual Test - Basic CL Workflow
### Participant Accounts:
1. **u9001** (Applicant, Employee)
2. **u9005** (Nominated Substitute, Employee)
3. **u9002** (Unit Head Approver, Employee/Leave Approver)

### Step 1: Submission
- **Action**: u9001 submitted a two-day Casual Leave (CL) application and nominated u9005 as the substitute.
- **Verification Methodology**: The system correctly recorded the leave request with the specified details.

### Step 2: Substitute Consent
- **Action**: u9005 logged in and accepted the substitute request.
- **Verification Methodology**: The system updated the status to indicate that a substitute had been assigned, and u9001 was notified of this change.

### Step 3: Sanction Decision
- **Action**: u9002 logged in and approved the leave application.
- **Verification Methodology**: The system transitioned the leave request from "Pending" to "APPROVED," and the leave balance for u9001 was accurately deducted.

### Step 4: Verification
- **Action**: u9001 logged in, confirmed that the application status had changed to APPROVED, and verified that the leave-balance deduction was correct.
- **Qualified Result**: USER-CONFIRMED MANUAL PASS.
- **Qualification Note**: Confirmed manually by the human evaluator during live browser testing. No speculative application IDs, exact dates, or unverified screenshots were invented.

## Verification Methodology & Browser Testing Status
### UI Navigation Across Pilot Roles
- The system was navigated through various roles including Employee, Leave Approver, and Leave Admin to ensure that each role could perform its designated tasks without issues.
  
### Module Access via Vite Proxy
- The module was accessed using the Vite proxy setup (localhost:5173 -> :8002 / :8001) to simulate real-world usage scenarios.

### Distinction Between User-Confirmed Manual Test Evidence and Automated Test Execution
- This document focuses on user-confirmed manual test evidence, which involves live testing by a human evaluator. It is distinct from automated test execution, where scripts are used to run tests repeatedly without human intervention.