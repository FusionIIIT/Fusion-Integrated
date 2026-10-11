import { Container, Title, Text } from "@mantine/core";

export default function ApplyLeavePage() {
  return (
    <Container size="lg" py="md">
      <Title order={2}>Apply for Leave</Title>
      <Text c="dimmed">Submit a new leave application.</Text>
    </Container>
  );
}
