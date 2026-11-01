import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { clubs } from "../data";

export default function ClubDirectoryPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string | null>("All");

  const filteredClubs = useMemo(() => {
    return clubs.filter((club) => {
      const matchesSearch =
        club.name.toLowerCase().includes(search.toLowerCase()) ||
        club.description.toLowerCase().includes(search.toLowerCase());

      const matchesCategory =
        category === "All" || category === null || club.category === category;

      return matchesSearch && matchesCategory;
    });
  }, [search, category]);

  return (
    <Stack gap="lg">
      <PageHeader
        title="Club Directory"
        subtitle="Search and explore the clubs available on campus."
      />

      <Group align="flex-end" grow>
        <TextInput
          label="Search clubs"
          placeholder="Enter a club name..."
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
        />
        <Select
          label="Category"
          value={category}
          onChange={setCategory}
          data={["All", "Technical", "Sports", "Cultural"]}
          allowDeselect={false}
        />
      </Group>

      <Text size="sm" c="dimmed">
        Showing {filteredClubs.length} of {clubs.length} clubs
      </Text>

      {filteredClubs.length > 0 ? (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {filteredClubs.map((club) => (
            <Card key={club.id} withBorder radius="md" padding="lg">
              <Group justify="space-between" mb="sm">
                <Title order={4}>{club.name}</Title>
                <Badge color={club.status === "Active" ? "green" : "yellow"}>
                  {club.status}
                </Badge>
              </Group>

              <Badge variant="light" mb="sm">{club.category}</Badge>

              <Text c="dimmed" size="sm" mb="md">
                {club.description}
              </Text>

              <Text size="sm" mb="md">
                {club.members} members
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
      ) : (
        <Card withBorder padding="xl" radius="md">
          <Stack align="center" gap="xs">
            <Title order={4}>No clubs found</Title>
            <Text c="dimmed" size="sm">
              Try changing your search or category.
            </Text>
          </Stack>
        </Card>
      )}

      <Text c="dimmed" size="xs">
        Demo directory — club information is sample data.
      </Text>
    </Stack>
  );
}
