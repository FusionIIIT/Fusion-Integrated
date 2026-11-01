import React, { useEffect, useState } from "react";
import { Badge, Card, Container, Stack, Table, Text, Title } from "@mantine/core";

interface UserItem {
  id: number;
  institute_id: string;
  email: string;
  user_type: string;
  status: string;
}

export default function UsersPage(): React.ReactElement {
  const [users, setUsers] = useState<UserItem[]>([]);

  useEffect(() => {
    fetch("/api/v1/superadmin/users/")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setUsers(data);
      })
      .catch(() => {});
  }, []);

  return (
    <Container size="xl" py="md">
      <Stack gap="md">
        <div>
          <Title order={2}>Super Admin: User Management</Title>
          <Text c="dimmed">Basic user account governance (BR-SA-001, BR-SA-002, BW-SA-08).</Text>
        </div>
        <Card shadow="xs" withBorder>
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Institute ID</Table.Th>
                <Table.Th>Email</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {users.map((u) => (
                <Table.Tr key={u.id}>
                  <Table.Td fw={500}>{u.institute_id}</Table.Td>
                  <Table.Td>{u.email}</Table.Td>
                  <Table.Td><Badge variant="dot">{u.user_type}</Badge></Table.Td>
                  <Table.Td><Badge color={u.status === "ACTIVE" ? "green" : "gray"}>{u.status}</Badge></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </Container>
  );
}
