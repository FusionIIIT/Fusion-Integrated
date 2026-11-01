import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function GovernancePage() {
  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="FTS Governance & Audit Logs"
        subtitle="System Administrator security oversight and usage audit logs"
      />
      <Stack mt="md">
        <Card withBorder p="md" radius="sm">
          <Text c="dimmed">No audit logs recorded.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
