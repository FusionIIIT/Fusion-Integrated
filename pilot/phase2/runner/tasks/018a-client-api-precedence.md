TITLE: Fix the four queryFn lines in the client data layer that tsc still rejects
FORMAT: diff
EDIT: client/src/modules/leave/api.ts
LIMIT: 600
POST: none
---
Task 010b did not fix item 1: tsc still reports TS2339/TS2345 on four lines because `.data` is read from the Promise instead of from the awaited response. Fix only these four lines, with four SEARCH/REPLACE edits (the parentheses must close right after the http.get(...) call, before .data):

1. In useMyApplications:
    queryFn: async () => asList(await http.get<LeaveApplication[]>("/leave/applications/").data),
becomes
    queryFn: async () => asList((await http.get<LeaveApplication[]>("/leave/applications/")).data),

2. In useApplicationDetail:
    queryFn: async () => (await http.get<LeaveApplication>(`/leave/applications/${id}/`).data),
becomes
    queryFn: async () => (await http.get<LeaveApplication>(`/leave/applications/${id}/`)).data,

3. In useInbox:
    queryFn: async () => asList(await http.get<LeaveApplication[]>("/leave/inbox/").data),
becomes
    queryFn: async () => asList((await http.get<LeaveApplication[]>("/leave/inbox/")).data),

4. In useBalances:
    queryFn: async () => asList(await http.get<LeaveBalance[]>("/leave/balances/", { params: { year } })),
becomes
    queryFn: async () => asList((await http.get<LeaveBalance[]>("/leave/balances/", { params: { year } })).data),

Do not change anything else.
