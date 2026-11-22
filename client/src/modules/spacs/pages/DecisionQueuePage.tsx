import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function DecisionQueuePage() {
  return (
    <Container size="xl">
      <PageHeader
        title="SPACS Decision Queue"
        subtitle="Review verified applications and record final scholarship sanctions or returns"
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          No verified applications awaiting final decision.
        </Text>
      </Card>
    </Container>
  );
}
