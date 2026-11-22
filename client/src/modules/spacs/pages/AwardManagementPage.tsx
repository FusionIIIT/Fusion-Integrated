import { Card, Container, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function AwardManagementPage() {
  return (
    <Container size="xl">
      <PageHeader
        title="Convocation Award Cycles"
        subtitle="Prepare candidate pools, coordinate committee evaluations, and record institutional approvals"
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          No active convocation award cycles in progress.
        </Text>
      </Card>
    </Container>
  );
}
