import { Card, SimpleGrid, Text, Title, Button, Group, Stack, Badge } from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { clubs } from "../data";

export default function DashboardPage() {
  const activeClubs = clubs.filter((club) => club.status === "Active").length;
  const totalMembers = clubs.reduce((sum, club) => sum + club.members, 0);

  const stats = [
    { label: "Total Clubs", value: clubs.length },
    { label: "Active Clubs", value: activeClubs },
    { label: "Total Members", value: totalMembers },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Gymkhana Dashboard"
        subtitle="Manage and explore student clubs and activities."
        action={
          <Button component={Link} to="/gymkhana/clubs">
            Explore Clubs
          </Button>
        }
      />

      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        {stats.map((stat) => (
          <Card key={stat.label} withBorder radius="md" padding="lg">
            <Text c="dimmed" size="sm">{stat.label}</Text>
            <Title order={2} mt={6}>{stat.value}</Title>
          </Card>
        ))}
      </SimpleGrid>

      <div>
        <Group justify="space-between" mb="md">
          <Title order={3}>Explore Clubs</Title>
          <Button component={Link} to="/gymkhana/clubs" variant="subtle">
            View all clubs
          </Button>
        </Group>

        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {clubs.slice(0, 3).map((club) => (
            <Card key={club.id} withBorder radius="md" padding="lg">
              <Group justify="space-between" mb="sm">
                <Title order={4}>{club.name}</Title>
                <Badge color={club.status === "Active" ? "green" : "yellow"}>
                  {club.status}
                </Badge>
              </Group>
              <Text c="dimmed" size="sm" mb="md">
                {club.description}
              </Text>
              <Text size="sm" mb="md">
                {club.category} · {club.members} members
              </Text>
              <Button
                component={Link}
                to={`/gymkhana/clubs/${club.id}`}
                variant="light"
                fullWidth
              >
                View Details
              </Button>
            </Card>
          ))}
        </SimpleGrid>
      </div>

      <Text c="dimmed" size="xs">
        Demo dashboard — currently displaying sample data.
      </Text>
    </Stack>
  );
}
