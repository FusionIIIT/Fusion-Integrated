# MMS implementation summary

The restored MMS implementation has been registered selectively on `module/mms` and corrected for the specified known defects.

The canonical module code is `mms`. Permission codes use `mms.*`; “Mess Management” remains the display label.

The implementation retains the frozen unresolved policy areas instead of inventing values:

- no Mess Admin menu grant
- no special-food decision-period default
- no rebate date-modification policy
- no special-food charge source, amount/rate, or value-selection rule; approval stays blocked until these are supplied by authoritative policy
- no cancelled-special-food billing treatment
- no vacation reminder cadence

The special-food API and Caretaker UI fail closed while the charge policy is absent. A caller-supplied amount is not treated as an authority source: approval returns HTTP 409 and leaves the request `requested`; Caretakers may reject it. No charge is added to a bill.

Student 1 agrees with the active Caretaker interpretation for Served/Cancelled updates in MMS-UC-021. The use case names the actor and gives those actions in its main scenario; the Problem Statement does not explicitly name the actor. This resolves the A9 specification reading only and does not decide cancellation billing.

Historical A8 designs, results, and tests remain under their existing isolated locations and are not Assignment 9 Student 2 spec-test work.
