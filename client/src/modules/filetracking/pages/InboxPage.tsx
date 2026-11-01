import { Card, Container, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function InboxPage() {
  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="File Inbox"
        subtitle="Files received and awaiting your review or action"
      />
      <Stack mt="md">
        <Card withBorder p="md" radius="sm">
          <Text c="dimmed">No pending files in inbox.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
