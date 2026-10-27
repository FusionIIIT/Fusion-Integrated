Review of SubstituteRequestsPage.tsx from task 014 (tsc reports 15 errors). React hooks must run in the same order on every render, but useInbox() is called after an early return. Fix only these, with SEARCH/REPLACE edits:

1. Change the first two import lines to:
import { Button, Card, Container, Group } from "@mantine/core";
and delete `import { useState } from "react";` (requestId is never used).
2. Change `import { DataTable } from "../../../ui/components/DataTable";` to `import { DataTable, type Column } from "../../../ui/components/DataTable";`.
3. Replace everything from `  const respondMutation = useSubstituteResponse();` down to and including the closing `  }` of the `if (applications.length === 0) {` block with:
  const respondMutation = useSubstituteResponse();
  const inboxData = useInbox();

  if (inboxData.error) {
    return (
      <Container size="xl">
        <PageHeader title="Substitute Requests" subtitle="Colleagues who nominated you as their substitute" />
        <ErrorState error={inboxData.error} />
      </Container>
    );
  }

  const applications = (inboxData.data ?? []).filter((app) => app.stage === "substitute");
4. Change `  const columns = [` to `  const columns: Column<LeaveApplication>[] = [`.
5. Both onSuccess notifications lack a message (TS2345). Use
      onSuccess: () => notifications.show({ color: "green", title: "Accepted", message: "The request now goes to the approver." }),
   in handleAccept and
      onSuccess: () => notifications.show({ color: "gray", title: "Declined", message: "Your colleague will nominate someone else." }),
   in handleDecline.
6. Wrap the DataTable in a Card and make it typed: `<DataTable` becomes `<Card padding="lg"><DataTable<LeaveApplication>`, `loading={respondMutation.isPending}` becomes `loading={inboxData.isPending}`, and after the DataTable's closing `/>` add `</Card>`.

Do not change anything else.
