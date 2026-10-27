TITLE: Rewrite MyLeavesPage again after 018c left a stray SEARCH block and the dead Withdraw button
FORMAT: whole
EDIT: client/src/modules/leave/pages/MyLeavesPage.tsx
READ: client/src/modules/leave/api.ts client/src/ui/components/DataTable.tsx
LIMIT: 1500
POST: none
---
Task 018c applied part of its edits but also pasted a raw "<<<<<<< SEARCH" block into the JSX (tsc: "Merge conflict marker encountered"), and it did not apply items 5, 7 and 8: withdraw() still only shows a notification, cancel() still calls the useCancel hook inside a handler (hooks may only be called at the top of a component), the table still reads applicationsData?.results (the hook returns a plain array), and the cancel condition compares Date objects.

Rewrite the whole file. Keep the imports and the ReplaceSubstitute component EXACTLY as they are now (they are correct). Then write MyLeavesPage with this structure:

export default function MyLeavesPage() {
  const { data: applicationsData, isPending: appsPending, error: appsError } = useMyApplications();
  const { data: balancesData } = useBalances(new Date().getFullYear());
  const withdrawMutation = useWithdraw();
  const cancelMutation = useCancel();
  const today = new Date().toISOString().slice(0, 10);

  if (appsError) return <Container size="xl"><ErrorState error={appsError} /></Container>;

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

  return (
    <Container size="xl">
      <PageHeader title="My Leaves" subtitle="Your leave balances and requests" />
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md" mb="md">
        {(balancesData ?? []).map((b: LeaveBalance) => ( ...one Card per balance, key={b.category}: label CATEGORY_LABELS[b.category], "Available {b.available} of {b.entitled}", "Used {b.used}"... ))}
      </SimpleGrid>
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={applicationsData ?? []}
          loading={appsPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[ ...seven columns, each { key, header, render: (r) => ... } ... ]}
          empty={{ title: "No leave requests yet", description: "Requests you apply for appear here." }}
        />
      </Card>
    </Container>
  );
}

The seven columns: Type (CATEGORY_LABELS[r.category] plus " (cancellation)" when r.kind === "cancellation"), Dates (`${r.start_date} to ${r.end_date}`), Days (r.days), Stage (r.stage.replace(/_/g, " ")), Status (<StatusBadge status={r.status} />), Substitute (<ReplaceSubstitute id={r.id} substituteId={r.substitute_id} status={r.substitute_status} />), and Actions: a Group with a "Withdraw" Button (size="xs", variant="subtle", onClick={() => withdraw(r)}) when r.status === "pending" && r.kind === "leave", and a "Cancel leave" Button (size="xs", variant="subtle", color="red", onClick={() => cancel(r)}) when r.status === "approved" && r.kind === "leave" && r.start_date > today.

Write the whole file. Do not ask for more files.
