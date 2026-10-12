---
owner: platform
status: reviewed
last-reviewed: 2026-10-12
---

# Leave counting and entitlement

This document states the baseline arithmetic. The authoritative values are the current configured
ELM policy; the defaults below are the synchronized baseline values.

## Annual entitlement

| Category | Eligibility | Annual credit | Year-end treatment |
|---|---|---:|---|
| CL | Faculty and Staff | 8 days | Unused balance lapses |
| RH | Faculty and Staff | 2 days | Unused balance lapses |
| SCL | Faculty and Staff | Up to 15 days | Unused balance lapses |
| EL | Non-faculty Staff | 30 days | Unused balance carries forward |
| VL | Faculty, only during an Academic Calendar vacation | 60 days | Unused VL converts to EL at 2:1 |
| COL | Eligible Faculty and Staff | 20 days | Unused balance carries forward |

SCL admissibility is decided by the final authority. The system does not invent a separate encoded
purpose list. COL medical evidence is requested only when current policy requires it.

## Counting an interval

- EL, COL, and VL count every date from start through end, inclusive. Saturdays, Sundays, and closed
  holidays inside the interval count.
- CL, SCL, and RH do not use that continuous-count rule. CL and SCL count chargeable working days
  after removing weekends and closed calendar holidays. RH is one day and must match an RH entry in
  the currently published calendar.
- A CL half day must be for one date and consumes 0.5. A first-half and second-half request may
  share a date; a full day cannot overlap either half.
- Cross-year periods are split by calendar year for validation and ledger posting. Each year's
  request portion must fit that year's available balance.
- Station Leave adds details to the same request. It does not create another leave category or
  account debit.

## Balance equations

For one employee, category, and year:

`available = sum(all immutable account entries for that employee/category/year)`

Entitlement, carry-in, approved use, cancellation reversal, resumption adjustment, and authorized
administrative correction are separate ledger entries. A rejected or withdrawn request creates no
leave debit. A final approval debits only the approved duration. A final cancellation approval
credits the exact original debit by year.

## Year-end event

At the configured boundary, the event closes the ending leave year and opens the next one. The
processor is idempotent and reports counts for closing, carry-forward, conversion, lapse, and
exceptions.

- CL, RH, and SCL unused balance is removed.
- EL and COL unused balance is debited from the closing year and credited to the next year at 1:1.
- Faculty VL unused balance is removed from VL and credited to next-year EL at 1 EL for every 2 VL.
  Fractional conversions are retained at the account's decimal precision.
- The next year's configured annual entitlement is credited once, separately from carry-in.
- Failed employee/category records are retried by the same source key and remain visible as
  operational exceptions; the year-end boundary is a system event, not a human actor.
