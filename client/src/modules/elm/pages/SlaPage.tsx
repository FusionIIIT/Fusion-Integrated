import { Container } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function SlaPage() {
  return (
    <Container size="lg">
      <PageHeader title="SLA" subtitle="Configure SLA thresholds and run processing" />
    </Container>
  );
}
