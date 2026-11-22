import { Alert, Badge, Card, Container, Group, Table, Text, Title } from "@mantine/core";

import { useProfiles } from "../api/hooks";

export default function ProfilesPage() {
  const { data: profiles, isLoading } = useProfiles();

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Directory</Title>
          <Text c="dimmed">Students, Faculty, and Alumni directory with privacy-masked profiles</Text>
        </div>
      </Group>

      {isLoading && <Text>Loading directory profiles...</Text>}

      {profiles && profiles.length === 0 && (
        <Alert title="No Profiles Found" color="blue">
          No directory profiles have been recorded for this department.
        </Alert>
      )}

      {profiles && profiles.length > 0 && (
        <Card withBorder shadow="sm" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>User ID</Table.Th>
                <Table.Th>Role / Type</Table.Th>
                <Table.Th>Office / Details</Table.Th>
                <Table.Th>Research / Batch</Table.Th>
                <Table.Th>Contact (Protected)</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {profiles.map((p) => (
                <Table.Tr key={p.id}>
                  <Table.Td fw={600}>{p.user_id}</Table.Td>
                  <Table.Td>
                    <Badge color={p.profile_type === "FACULTY" ? "indigo" : p.profile_type === "STUDENT" ? "teal" : "gray"}>
                      {p.profile_type}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{p.office_room || p.batch_or_roll || "-"}</Table.Td>
                  <Table.Td>{p.research_interests || p.graduation_year || "-"}</Table.Td>
                  <Table.Td>
                    {p.contact_phone ? (
                      <Text size="sm">{p.contact_phone}</Text>
                    ) : (
                      <Badge variant="dot" color="gray">Masked for Privacy</Badge>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Container>
  );
}
