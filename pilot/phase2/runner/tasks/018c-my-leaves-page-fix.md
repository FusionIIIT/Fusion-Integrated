TITLE: Fix the 17 TypeScript errors and the dead Withdraw button in MyLeavesPage
FORMAT: diff
EDIT: client/src/modules/leave/pages/MyLeavesPage.tsx
READ: client/src/modules/leave/api.ts client/src/ui/components/DataTable.tsx
LIMIT: 1200
POST: none
---
Review of MyLeavesPage.tsx from task 012 (tsc reports 17 errors). The mutation hooks take NO argument; the id goes into mutate(). Hooks may only be called at the top of a component, never inside a handler. Fix only these, with SEARCH/REPLACE edits:

1. Import the balance type: change `  type LeaveApplication,` in the "../api" import to `  type LeaveApplication, type LeaveBalance,`.
2. In ReplaceSubstitute: replace `const mutate = useReplaceSubstitute(id);` with `const replace = useReplaceSubstitute();`, and replace the body of handleSubmit with:
    if (!subId) return;
    replace.mutate({ id, substitute_id: Number(subId) }, {
      onSuccess: () => notifications.show({ color: "green", title: "Substitute nominated", message: "Your new substitute has been asked to confirm." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not nominate", message: errorMessage(e) }),
    });
3. In ReplaceSubstitute, the NumberInput's `onChange={setSubId}` must become `onChange={(v) => setSubId(String(v))}`.
4. In MyLeavesPage, replace the two lines
  const { data: balancesData, isPending: balancesPending } = useBalances(new Date().getFullYear());
  const [historyFor, setHistoryFor] = useState<number | null>(null);
with
  const { data: balancesData } = useBalances(new Date().getFullYear());
  const withdrawMutation = useWithdraw();
  const cancelMutation = useCancel();
  const today = new Date().toISOString().slice(0, 10);
5. The withdraw function only shows a notification and never calls the server. Replace the whole withdraw function and the whole cancel function with:
  function withdraw(app: LeaveApplication) {
    withdrawMutation.mutate({ id: app.id }, {
      onSuccess: () => notifications.show({ color: "gray", title: "Withdrawn", message: "Your application has been withdrawn." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not withdraw", message: errorMessage(e) }),
    });
  }

  function cancel(app: LeaveApplication) {
    cancelMutation.mutate({ id: app.id }, {
      onSuccess: () => notifications.show({ color: "blue", title: "Cancellation requested", message: "Your cancellation request has been sent for approval." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not cancel", message: errorMessage(e) }),
    });
  }
6. Mantine 7 SimpleGrid has spacing, not gap: change `<SimpleGrid cols={1} gap="md" mb="md">` to `<SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md" mb="md">`.
7. The hooks return plain arrays, not pages: change `{balancesData?.results?.map((b: LeaveBalance) => (` to `{(balancesData ?? []).map((b: LeaveBalance) => (`, and `rows={(applicationsData?.results ?? []) as LeaveApplication[]}` to `rows={applicationsData ?? []}`.
8. A leave can only be cancelled before it starts (BR-EL-023): change `new Date(r.start_date) >= new Date()` to `r.start_date > today`.

Do not change anything else.
