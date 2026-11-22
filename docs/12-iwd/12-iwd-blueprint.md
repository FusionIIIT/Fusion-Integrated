# Architecture Blueprint: Institute Works Department (IWD) - Module 12

## 1. Executive Summary
The Institute Works Department (IWD) module digitizes and manages civil and electrical campus maintenance for IIITDM Jabalpur. It enforces strict cost-band routing, role-based approval hierarchies, inventory coordination, physical work verification, auditing, and financial settlement.

## 2. Distinct Roles & Actors
- **Institute Employee (`employee`)**: Submits complaints, views tracking, provides post-repair feedback.
- **Engineer (`engineer`)**: Assesses complaints, prepares estimates, executes work, submits final bills.
- **IWD Admin (`admin`)**: Oversees stock availability, issues material, approves low-cost quotations.
- **Department Head (`hod`)**: Reviews mid-range estimates after committee review; performs preliminary quality verification.
- **Dean (`dean`)**: Distinct approval role; not aliased to HOD.
- **Director (`director`)**: Approves high-cost works (> Rs. 2.5L), authorizes external bidding, gives final settlement approval.
- **Auditor (`auditor`)**: Cross-checks completed work against approved estimates and validates invoices.
- **Accounts (`accounts`)**: Final payment execution.

## 3. Cost-Band Approval Rules
- **Low-Cost (< Rs. 25,000)**: Approved by IWD Admin directly.
- **Mid-Range (Rs. 25,000 to Rs. 2,50,000)**: Mandatory Review Committee evaluation -> Department Head (Approve / Reject / Forward to Director).
- **High-Cost (> Rs. 2,50,000)**: Director approval & external competitive bidding.

## 4. Work Verification & Settlement State Sequence
`SUBMITTED` -> `ASSIGNED` -> `ASSESSED` -> `ESTIMATE_APPROVED` -> `IN_PROGRESS` -> `COMPLETED` -> `VERIFIED` -> `RESOLVED` -> `CLOSED`.
Payment settlement strictly requires:
1. `PhysicalVerification.passed == True`
2. `FinalBill.auditor_verified == True`
3. `FinalBill.director_approved == True`
4. Settlement performed by `Accounts` role.
