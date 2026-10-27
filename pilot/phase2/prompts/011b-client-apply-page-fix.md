Review of ApplyLeavePage.tsx from task 011 (tsc reports 3 errors). Fix only these, with SEARCH/REPLACE edits:

1. Select onChange receives (value: string | null), not LeaveCategory (TS2322). Use: onChange={(value) => value && handleCategoryChange(value as LeaveCategory)}
2. Mantine 7 Checkbox onChange receives a ChangeEvent, not a boolean (TS2322). Use: onChange={(e) => setFormData({ ...formData, station_leave: e.currentTarget.checked })}
3. NumberInput onChange receives string | number, but substitute_id is a string in the form state (TS2322). Use: onChange={(value) => setFormData({ ...formData, substitute_id: String(value) })}
4. handleSubmit rejects every half-day choice for a single-day CL, which is the one case where half days are allowed (BR-EL-010). Delete the whole "Additional validation for half_day" if-block, and in the mutate payload send `half_day: showHalfDaySelect ? formData.half_day : "none"`.
5. The payload sends `station_address: formData.station_address || null`, but the server rejects null. Send `station_address: formData.station_address`.
6. The submit Button has `leftSection={<span>Submit</span>}`, which prints "Submit" twice. Remove that leftSection prop.

Do not change anything else.
