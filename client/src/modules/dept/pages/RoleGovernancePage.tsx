import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Modal, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { useAssignRole, useRoleAssignments } from "../api/hooks";

export default function RoleGovernancePage() {
  const { can } = useAuth();
  const { data: roles, isLoading } = useRoleAssignments();
  const assignRole = useAssignRole();

  const [createOpened, setCreateOpened] = useState(false);
  const [roleName, setRoleName] = useState<"HOD" | "DEPT_ADMIN">("HOD");
  const [userId, setUserId] = useState("");
  const [startDate, setStartDate] = useState("2026-08-01T00:00:00Z");
  const [endDate, setEndDate] = useState("2028-07-31T23:59:59Z");

  const canManage = can("dept.role_assignment.manage");

  const handleAssign = async () => {
    if (!userId.trim()) return;
    await assignRole.mutateAsync({
      role_name: roleName,
      user_id: userId,
      start_date: startDate,
      end_date: endDate,
    });
    setUserId("");
    setCreateOpened(false);
  };

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Role Governance</Title>
          <Text c="dimmed">Central administrative tenure assignments for HOD and Dept_Admin</Text>
        </div>
        {canManage && (
          <Button onClick={() => setCreateOpened(true)}>Assign Role Tenure</Button>
        )}
      </Group>

      {isLoading && <Text>Loading assignments...</Text>}

      {roles && roles.length === 0 && (
        <Alert title="No Role Tenures Recorded" color="blue">
          There are no time-bound role assignments recorded for this department.
        </Alert>
      )}

      {roles && roles.length > 0 && (
        <Card withBorder shadow="sm" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Role</Table.Th>
                <Table.Th>User ID</Table.Th>
                <Table.Th>Start Date</Table.Th>
                <Table.Th>End Date</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {roles.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td fw={700}>
                    <Badge color={r.role_name === "HOD" ? "indigo" : "cyan"}>{r.role_name}</Badge>
                  </Table.Td>
                  <Table.Td>{r.user_id}</Table.Td>
                  <Table.Td>{new Date(r.start_date).toLocaleDateString()}</Table.Td>
                  <Table.Td>{new Date(r.end_date).toLocaleDateString()}</Table.Td>
                  <Table.Td>
                    <Badge color={r.status === "ACTIVE" ? "green" : r.status === "SCHEDULED" ? "blue" : "gray"}>
                      {r.status}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Assign Department Role">
        <Stack gap="sm">
          <Select
            label="Role"
            data={[
              { value: "HOD", label: "Head of Department (HOD)" },
              { value: "DEPT_ADMIN", label: "Department Administrator" },
            ]}
            value={roleName}
            onChange={(val) => setRoleName((val as "HOD" | "DEPT_ADMIN") ?? "HOD")}
            required
          />
          <TextInput label="User ID / Username" placeholder="e.g. faculty_user" value={userId} onChange={(e) => setUserId(e.target.value)} required />
          <TextInput label="Start Date (ISO)" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
          <TextInput label="End Date (ISO)" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateOpened(false)}>Cancel</Button>
            <Button onClick={handleAssign} loading={assignRole.isPending}>Assign</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
