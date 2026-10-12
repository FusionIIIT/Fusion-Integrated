import { Container } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ApprovalsPage() {
  return (
    <Container size="lg">
      <PageHeader title="Approvals" subtitle="Tasks awaiting your action" />
    </Container>
  );
}
