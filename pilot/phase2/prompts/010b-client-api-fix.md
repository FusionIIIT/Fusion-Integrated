Review of client/src/modules/leave/api.ts from task 010 (tsc reports 5 errors in it). Keep the types, CATEGORY_LABELS, asList and the hook names, and rewrite the whole file fixing all of these:

1. `await http.get<X>(url).data` reads .data from the Promise, not from the response (TS2339). Every query must be written as `(await http.get<X>(url, config)).data`, and asList(...) wraps that whole expression.
2. Wrong paths. Every application endpoint is under /leave/applications/ (see modules/leave/api/urls.py): `/leave/applications/${id}/`, `/leave/applications/${id}/withdraw/`, `/leave/applications/${id}/cancel/`, `/leave/applications/${id}/substitute-response/`, `/leave/applications/${id}/replace-substitute/`, `/leave/applications/${id}/decide/`. Balances are GET "/leave/balances/" with `{ params: { year } }`; the year is NOT in the path.
3. The mutations take the id as a hook argument (useWithdraw(id)), but the pages call one hook and then mutate for whichever row was clicked. Each mutation hook takes no argument and receives the id in mutate():
   useWithdraw(): mutationFn: async (vars: { id: number }) => ...
   useCancel(): vars { id: number }
   useSubstituteResponse(): vars { id: number; accept: boolean }, posts { accept }
   useReplaceSubstitute(): vars { id: number; substitute_id: number }, posts { substitute_id }
   useDecide(): vars { id: number; decision: Decision; remark: string }, posts { decision, remark }
   useApply() stays as it is.
4. Types must match the serializers: LeaveApplication.parent is number | null (the serializer sends the parent's id), station_address is string, there is no updated_at field (remove it), LeaveAction.remark is string. ApplyInput.station_address is string, because the server rejects null.

Write the whole file. Do not ask for more files.
