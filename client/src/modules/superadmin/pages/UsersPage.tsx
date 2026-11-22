import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import {
  useArchiveUser,
  useCreateUser,
  useDeactivateUser,
  useReactivateUser,
  useRestoreUser,
  useUsers,
} from "../api/hooks";
import type { UserAccount, UserActivationStatus } from "../api/types";

function statusColor(status: UserActivationStatus) {
  switch (status) {
    case "ACTIVE":
      return "green";
    case "DEACTIVATED":
      return "orange";
    case "ARCHIVED_REVERSIBLE":
      return "blue";
    case "ARCHIVED_PERMANENT":
      return "gray";
    default:
      return "gray";
  }
}

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const { data: users, isLoading, isError } = useUsers({ search });

  const [createOpened, setCreateOpened] = useState(false);
  const [instituteId, setInstituteId] = useState("");
  const [userIdVal, setUserIdVal] = useState("");
  const [email, setEmail] = useState("");
  const [userType, setUserType] = useState("STUDENT");

  const createMutation = useCreateUser();
  const deactivateMutation = useDeactivateUser();
  const reactivateMutation = useReactivateUser();
  const archiveMutation = useArchiveUser();
  const restoreMutation = useRestoreUser();

  const handleCreate = () => {
    createMutation.mutate(
      {
        user_id: parseInt(userIdVal, 10),
        institute_id: instituteId,
        email,
        user_type: userType,
        program: userType === "STUDENT" ? "B.Tech" : "",
        batch: userType === "STUDENT" ? "2024" : "",
        department: userType !== "STUDENT" ? "CSE" : "",
      },
      {
        onSuccess: () => {
          setCreateOpened(false);
          setInstituteId("");
          setUserIdVal("");
          setEmail("");
        },
      },
    );
  };

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>User Accounts</Title>
          <Text c="dimmed">Manage institutional user accounts, activation, and lifecycle.</Text>
        </div>
        <Button onClick={() => setCreateOpened(true)}>Create Account</Button>
      </Group>

      <TextInput
        placeholder="Search by Institute ID or email..."
        value={search}
        onChange={(e) => setSearch(e.currentTarget.value)}
        aria-label="Search users"
      />

      {isLoading && (
        <Stack align="center" justify="center" p="xl" data-testid="loading-spinner">
          <Loader size="lg" />
          <Text c="dimmed">Loading user accounts...</Text>
        </Stack>
      )}

      {isError && (
        <Alert color="red" title="Error loading users" data-testid="error-message">
          Failed to retrieve user accounts from the server.
        </Alert>
      )}

      {!isLoading && !isError && users?.length === 0 && (
        <Alert color="blue" title="No users found" data-testid="empty-message">
          No user accounts found matching your filter criteria.
        </Alert>
      )}

      {!isLoading && !isError && users && users.length > 0 && (
        <Table withTableBorder striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>User ID</Table.Th>
              <Table.Th>Institute ID</Table.Th>
              <Table.Th>Email</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((u: UserAccount) => (
              <Table.Tr key={u.id}>
                <Table.Td>{u.user_id}</Table.Td>
                <Table.Td fw={500}>{u.institute_id}</Table.Td>
                <Table.Td>{u.email}</Table.Td>
                <Table.Td>{u.user_type}</Table.Td>
                <Table.Td>
                  <Badge color={statusColor(u.activation_status)}>{u.activation_status}</Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {u.activation_status === "ACTIVE" && (
                      <Button
                        size="xs"
                        color="orange"
                        variant="light"
                        onClick={() => deactivateMutation.mutate({ userId: u.user_id, reason: "Administrative deactivation" })}
                      >
                        Deactivate
                      </Button>
                    )}
                    {u.activation_status === "DEACTIVATED" && (
                      <>
                        <Button
                          size="xs"
                          color="green"
                          variant="light"
                          onClick={() => reactivateMutation.mutate({ userId: u.user_id, reason: "Administrative reactivation" })}
                        >
                          Reactivate
                        </Button>
                        <Button
                          size="xs"
                          color="blue"
                          variant="light"
                          onClick={() => archiveMutation.mutate({ userId: u.user_id, reason: "Archival after deactivation" })}
                        >
                          Archive
                        </Button>
                      </>
                    )}
                    {u.activation_status === "ARCHIVED_REVERSIBLE" && (
                      <Button
                        size="xs"
                        color="teal"
                        variant="light"
                        onClick={() => restoreMutation.mutate({ userId: u.user_id, reason: "Reversible restoration" })}
                      >
                        Restore
                      </Button>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Create User Account">
        <Stack gap="sm">
          <TextInput
            label="User ID"
            placeholder="e.g. 101"
            value={userIdVal}
            onChange={(e) => setUserIdVal(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Institute ID"
            placeholder="e.g. 24BCS170"
            value={instituteId}
            onChange={(e) => setInstituteId(e.currentTarget.value)}
            required
          />
          <TextInput
            label="Institute Email"
            placeholder="name@iiitdmj.ac.in"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
            required
          />
          <Select
            label="User Type"
            data={["STUDENT", "FACULTY", "STAFF"]}
            value={userType}
            onChange={(val) => setUserType(val || "STUDENT")}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={createMutation.isPending}>Create</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
