import { Container, Card, Stack, Text, Title } from "@mantine/core";
import { FaCalendarAlt } from "react-icons/fa";

interface Props {
  title?: string;
}

export default function PlaceholderPage({ title = "Leave Management" }: Props) {
  return (
    <Container size="md" py="xl">
      <Card padding="xl" withBorder radius="md">
        <Stack align="center" gap="sm">
          <FaCalendarAlt size={36} color="var(--mantine-color-blue-6)" />
          <Title order={3}>{title}</Title>
          <Text c="dimmed" size="sm" ta="center">
            The Employee Leave Management (ELM) backend is active. API endpoints are operational at /api/v1/elm/.
          </Text>
        </Stack>
      </Card>
    </Container>
  );
}
