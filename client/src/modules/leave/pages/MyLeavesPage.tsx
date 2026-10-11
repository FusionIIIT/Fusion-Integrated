import { Container, Title, Text } from "@mantine/core";

export default function MyLeavesPage() {
  return (
    <Container size="lg" py="md">
      <Title order={2}>My Leaves</Title>
      <Text c="dimmed">View history and status of your leave requests.</Text>
    </Container>
  );
}
