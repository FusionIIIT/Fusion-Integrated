import { Container } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { ApplicationsTable, WorkQueue } from "../components/Lists";

// UC-PMS-007, 010, 027: what PCC_ADMIN has to assign, route or resolve.
export default function AssignmentsPage() {
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Assignments" subtitle="Applications waiting for a Director or an attorney" />
      <WorkQueue kinds={["assign_director", "assign_attorney", "escalated_budget",
        "licensing_unrouted"]} emptyTitle="Nothing is waiting to be assigned" />
      <ApplicationsTable emptyTitle="No submitted applications yet" />
    </Container>
  );
}
