import { Badge, Card, Container, Group, Stack, Text } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ClubsPage() {
  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <PageHeader title="Gymkhana Clubs" subtitle="Browse active student clubs, technical teams, and cultural groups." />
        <Card withBorder padding="md">
          <Group justify="space-between">
            <Text fw={600}>Technical, Cultural & Sports Clubs</Text>
            <Badge color="blue">Active</Badge>
          </Group>
          <Text size="sm" c="dimmed" mt="xs">
            Explore approved student clubs, view leadership contacts, and submit membership applications.
          </Text>
        </Card>
      </Stack>
    </Container>
  );
}
