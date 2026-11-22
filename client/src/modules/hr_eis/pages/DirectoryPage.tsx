import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { FaSearch, FaUserTie } from "react-icons/fa";
import { useProfiles } from "../api/hooks";
import type { EmployeeProfile } from "../api/types";

export default function DirectoryPage() {
  const { data: profiles, isLoading, error } = useProfiles();
  const [searchTerm, setSearchTerm] = useState("");

  if (isLoading) {
    return (
      <Container size="xl" py="xl">
        <Group justify="center" py="xl">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="xl" py="xl">
        <Text c="red">Failed to load employee directory: {error.message}</Text>
      </Container>
    );
  }

  const list: EmployeeProfile[] = Array.isArray(profiles) ? profiles : [];
  const filtered = list.filter((p) => {
    const term = searchTerm.toLowerCase();
    return (
      p.username.toLowerCase().includes(term) ||
      p.pf_number.toLowerCase().includes(term) ||
      p.department.toLowerCase().includes(term) ||
      p.designation.toLowerCase().includes(term)
    );
  });

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={3}>Employee Directory</Title>
            <Text c="dimmed" size="sm">
              Staff view of institutional employees and professional records
            </Text>
          </div>
          <TextInput
            placeholder="Search by name, PF, dept..."
            leftSection={<FaSearch size={14} />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.currentTarget.value)}
            w={280}
          />
        </Group>

        {filtered.length === 0 ? (
          <Card withBorder padding="xl" radius="md">
            <Text c="dimmed" ta="center">
              No employee profiles matched your search query.
            </Text>
          </Card>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
            {filtered.map((emp) => (
              <Card key={emp.id} withBorder padding="md" radius="md" shadow="xs">
                <Group align="flex-start" gap="md">
                  <FaUserTie size={32} color="#4A90E2" />
                  <Stack gap={2} style={{ flex: 1 }}>
                    <Text fw={600} size="sm">
                      {emp.username}
                    </Text>
                    <Group gap={6}>
                      <Badge size="xs" color="blue" variant="light">
                        {emp.designation}
                      </Badge>
                      <Badge size="xs" color="gray" variant="outline">
                        {emp.department}
                      </Badge>
                    </Group>
                    <Text size="xs" c="dimmed" mt={4}>
                      PF Number: {emp.pf_number}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Experiences: {emp.experiences?.length ?? 0}
                    </Text>
                  </Stack>
                </Group>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Stack>
    </Container>
  );
}
