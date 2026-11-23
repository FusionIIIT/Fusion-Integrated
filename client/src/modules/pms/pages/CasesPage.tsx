import { Container } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { ApplicationsTable, WorkQueue } from "../components/Lists";

// UC-PMS-011..015, 017, 033: cases offered to or accepted by this attorney.
export default function CasesPage() {
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Assigned Cases" subtitle="Offers to answer and cases you are working on" />
      <WorkQueue kinds={["case"]} emptyTitle="No cases are offered or open" />
      <ApplicationsTable emptyTitle="No cases yet" />
    </Container>
  );
}
