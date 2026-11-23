import { Container } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { ApplicationsTable, WorkQueue } from "../components/Lists";

// UC-PMS-008, 009, 018, 023: decisions waiting on this Director.
export default function ReviewsPage() {
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Reviews" subtitle="Reviews, appeals, budgets and renewals for you to decide" />
      <WorkQueue kinds={["review", "appeal", "budget", "renewal", "licensing"]}
        emptyTitle="No decisions are waiting on you" />
      <ApplicationsTable emptyTitle="No applications in your areas yet" />
    </Container>
  );
}
