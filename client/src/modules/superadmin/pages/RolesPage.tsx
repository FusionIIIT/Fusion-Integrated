import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { useAssignRole, useExtendRole, useRevokeRole, useRoles } from "../api/hooks";
import type { RoleAssignment } from "../api/types";

export default function RolesPage() {
  const [roleNameSearch, setRoleNameSearch] = useState("");
  const { data: roles, isLoading, isError } = useRoles({ role_name: roleNameSearch });

  const [assignOpened, setAssignOpened] = useState(false);
  const [targetUserId, setTargetUserId] = useState("");
  const [roleName, setRoleName] = useState("");

  const assignMutation = useAssignRole();
  const extendMutation = useExtendRole();
  const revokeMutation = useRevokeRole();

  const handleAssign = () => {
    const now = new Date();
    const nextYear = new Date();
    nextYear.setFullYear(now.getFullYear() + 1);

    assignMutation.mutate(
      {
        user_id: parseInt(targetUserId, 10),
        role_name: roleName,
        valid_from: now.toISOString(),
        valid_to: nextYear.toISOString(),
        reason: "Administrative assignment",
      },
      {
        onSuccess: () => {
          setAssignOpened(false);
          setTargetUserId("");
          setRoleName("");
        },
      },
    );
  };

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Role Assignments</Title>
          <Text c="dimmed">Manage institutional additional roles, validity windows, and extensions.</Text>
        </div>
        <Button onClick={() => setAssignOpened(true)}>Assign Role</Button>
      </Group>

      <TextInput
        placeholder="Filter by role name..."
        value={roleNameSearch}
        onChange={(e) => setRoleNameSearch(e.currentTarget.value)}
        aria-label="Filter roles"
      />

      {isLoading && (
        <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
          <Loader size="lg" />
          <Text c="dimmed">Loading role assignments...</Text>
        </Stack>
      )}

      {isError && (
        <Alert color="red" title="Error loading roles" data-testid="error-message">
          Failed to retrieve role assignments from the server.
        </Alert>
      )}

      {!isLoading && !isError && roles?.length === 0 && (
        <Alert color="blue" title="No roles found" data-testid="empty-message">
          No role assignments found matching criteria.
        </Alert>
      )}

      {!isLoading && !isError && roles && roles.length > 0 && (
        <Table withTableBorder striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>User ID</Table.Th>
              <Table.Th>Role Name</Table.Th>
              <Table.Th>Valid From</Table.Th>
              <Table.Th>Valid To</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {roles.map((r: RoleAssignment) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.user_id}</Table.Td>
                <Table.Td fw={500}>{r.role_name}</Table.Td>
                <Table.Td>{new Date(r.valid_from).toLocaleDateString()}</Table.Td>
                <Table.Td>{r.valid_to ? new Date(r.valid_to).toLocaleDateString() : "Indefinite"}</Table.Td>
                <Table.Td>
                  <Badge color={r.status === "ACTIVE" ? "green" : r.status === "SCHEDULED" ? "blue" : "gray"}>
                    {r.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {(r.status === "ACTIVE" || r.status === "EXTENDED") && (
                      <>
                        <Button
                          size="xs"
                          variant="light"
                          color="blue"
                          onClick={() => {
                            const extDate = new Date();
                            extDate.setFullYear(extDate.getFullYear() + 2);
                            extendMutation.mutate({
                              assignmentId: r.id,
                              new_valid_to: extDate.toISOString(),
                              reason: "Annual extension",
                            });
                          }}
                        >
                          Extend
                        </Button>
                        <Button
                          size="xs"
                          variant="light"
                          color="red"
                          onClick={() => revokeMutation.mutate({ assignmentId: r.id, reason: "Administrative revocation" })}
                        >
                          Revoke
                        </Button>
                      </>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={assignOpened} onClose={() => setAssignOpened(false)} title="Assign Role">
        <Stack gap="sm">
          <TextInput
            label="Target User ID"
            placeholder="e.g. 101"
            value={targetUserId}
            onChange={(e) => setTargetUserId(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Role Name"
            placeholder="e.g. Placement Coordinator"
            value={roleName}
            onChange={(e) => setRoleName(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAssignOpened(false)}>Cancel</Button>
            <Button onClick={handleAssign} loading={assignMutation.isPending}>Assign</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
