import { Container, Title, Text } from "@mantine/core";

export default function LeaveBalancesPage() {
  return (
    <Container size="lg" py="md">
      <Title order={2}>Leave Balances</Title>
      <Text c="dimmed">Current balance overview for all leave categories.</Text>
    </Container>
  );
}
