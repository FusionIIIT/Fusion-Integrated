import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function OutboxPage() {
  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="File Outbox"
        subtitle="Files you have forwarded or returned in circulation"
      />
      <Stack mt="md">
        <Card withBorder p="md" radius="sm">
          <Text c="dimmed">No files currently in outbox circulation.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
