import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function VerificationQueuePage() {
  return (
    <Container size="xl">
      <PageHeader
        title="SPACS Verification Queue"
        subtitle="Review assigned applications, verify supporting documents, or request corrections"
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          No pending applications requiring verification in your queue.
        </Text>
      </Card>
    </Container>
  );
}
