import { Container, Title, Text } from "@mantine/core";

export default function LeaveApprovalsPage() {
  return (
    <Container size="lg" py="md">
      <Title order={2}>Leave Approvals</Title>
      <Text c="dimmed">Review pending leave applications from your department.</Text>
    </Container>
  );
}
