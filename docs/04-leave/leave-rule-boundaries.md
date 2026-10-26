# Leave rule boundaries

This note records the behavior implemented in `modules/leave`; it does not
replace the institute's leave policy.

- A request counts weekdays in an inclusive date range. Saturdays and Sundays
  are excluded.
- Public holidays are not modeled, so a weekday holiday currently counts as a
  leave day.
- A request is counted in whole days. Half-day requests are not supported,
  although balances can contain fractional carried or allocated values.
- A request cannot span calendar years because each balance is configured for
  one year.
- Pending and approved requests reserve balance. Rejected and cancelled
  requests do not.

The assignment brief does not specify holiday or half-day policy. Confirm those
rules against the institute's ELM specification before changing this behavior.
