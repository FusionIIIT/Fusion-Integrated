import { useState } from "react";
import {
  Avatar,
  Badge,
  Card,
  Container,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { FaUsers } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDepartments, useProfiles } from "../api/hooks";

export default function FacultyStaffPage() {
  const { data: depts } = useDepartments();
  const defaultDept = depts?.[0];
  const deptId = defaultDept?.id;

  const { data: profiles, isPending, error } = useProfiles(deptId);
  const [filterKind, setFilterKind] = useState<string>("all");

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  const rows = (profiles || []).filter((p) => {
    if (filterKind === "all") return true;
    return p.kind?.toLowerCase() === filterKind.toLowerCase();
  });

  return (
    <Container size="lg">
      <PageHeader
        title="Faculty & Staff Directory"
        subtitle="Department academic personnel, research scholars, and administrative staff"
      />

      <Group justify="space-between" mb="md">
        <Select
          label="Filter by Role"
          size="xs"
          data={[
            { value: "all", label: "All personnel" },
            { value: "faculty", label: "Faculty" },
            { value: "staff", label: "Staff" },
            { value: "student", label: "Students" },
          ]}
          value={filterKind}
          onChange={(v) => setFilterKind(v || "all")}
          style={{ width: 180 }}
        />
        <Text size="xs" c="dimmed" mt="auto">
          Showing {rows.length} member(s)
        </Text>
      </Group>

      {isPending && <Text c="dimmed">Loading directory…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={6}>
            <FaUsers size={28} color="var(--mantine-color-gray-5)" />
            <Title order={4}>No profiles found</Title>
            <Text size="sm" c="dimmed">
              No department profiles match the selected role.
            </Text>
          </Stack>
        </Card>
      )}

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        {rows.map((p) => (
          <Card key={p.id} padding="md" withBorder>
            <Group align="flex-start">
              <Avatar size="lg" radius="xl" color="blue">
                {p.display_name ? p.display_name.slice(0, 2).toUpperCase() : "U"}
              </Avatar>
              <Stack gap={2} style={{ flex: 1 }}>
                <Text fw={700} size="sm">
                  {p.display_name || `User #${p.user_id}`}
                </Text>
                {p.kind && (
                  <Badge variant="light" size="xs" color="indigo" w="fit-content">
                    {p.kind}
                  </Badge>
                )}
                {p.discipline && (
                  <Text size="xs" c="dimmed">
                    {p.discipline} {p.programme ? `(${p.programme})` : ""}
                  </Text>
                )}
                {p.batch_year && (
                  <Text size="xs" c="dimmed">
                    Batch: {p.batch_year}
                  </Text>
                )}
                {p.notes && (
                  <Text size="xs" mt={4} style={{ whiteSpace: "pre-wrap" }}>
                    {p.notes}
                  </Text>
                )}
              </Stack>
            </Group>
          </Card>
        ))}
      </SimpleGrid>
    </Container>
  );
}
