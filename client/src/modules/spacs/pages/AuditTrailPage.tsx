import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function AuditTrailPage() {
  return (
    <Container size="xl">
      <PageHeader
        title="SPACS Audit Trail"
        subtitle="Immutable timestamped log of significant actions across the module lifecycle"
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          Audit events for catalogue, application, verification, decision, and publication actions.
        </Text>
      </Card>
    </Container>
  );
}
