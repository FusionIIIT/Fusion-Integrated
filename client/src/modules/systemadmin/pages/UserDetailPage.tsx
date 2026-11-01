import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Stack,
  Paper,
  Title,
  Text,
  Badge,
  Group,
  SimpleGrid,
  Button,
  Timeline,
  Table,
  Alert,
  Loader,
} from "@mantine/core";
import { FaArrowLeft, FaEdit, FaUserSlash, FaUserCheck, FaArchive } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useUser } from "../api/hooks";
import { EditUserModal, ChangeStatusModal } from "../components/UserModals";
import { ArchiveUserModal } from "../components/ArchivalModals";

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const userId = id ? parseInt(id, 10) : undefined;
  const { data: user, isLoading, error } = useUser(userId);

  const [editOpen, setEditOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);

  if (isLoading) {
    return (
      <Stack align="center" justify="center" p="xl" style={{ minHeight: 300 }}>
        <Loader />
        <Text c="dimmed">Loading user details...</Text>
      </Stack>
    );
  }

  if (error || !user) {
    return (
      <Alert color="red" title="User Not Found">
        User record could not be loaded. <Link to="/systemadmin/users">Return to directory</Link>
      </Alert>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between">
        <Button
          variant="subtle"
          leftSection={<FaArrowLeft size={14} />}
          component={Link}
          to="/systemadmin/users"
        >
          Back to Directory
        </Button>
        <Group gap="sm">
          <Button
            variant="default"
            leftSection={<FaEdit size={14} />}
            onClick={() => setEditOpen(true)}
            disabled={user.status === "archived"}
          >
            Edit Profile
          </Button>
          {user.status === "active" ? (
            <Button
              color="red"
              variant="light"
              leftSection={<FaUserSlash size={14} />}
              onClick={() => setStatusOpen(true)}
            >
              Deactivate Account
            </Button>
          ) : user.status === "deactivated" ? (
            <Group gap="xs">
              <Button
                color="green"
                variant="light"
                leftSection={<FaUserCheck size={14} />}
                onClick={() => setStatusOpen(true)}
              >
                Reactivate Account
              </Button>
              <Button
                color="orange"
                variant="light"
                leftSection={<FaArchive size={14} />}
                onClick={() => setArchiveOpen(true)}
              >
                Archive User
              </Button>
            </Group>
          ) : null}
        </Group>
      </Group>

      <PageHeader
        title={user.full_name}
        subtitle={`Basic User Identity Profile (${user.institute_id})`}
      />

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {/* Core Profile Card */}
        <Paper withBorder p="md" radius="md">
          <Title order={4} mb="md">Institutional Identity</Title>
          <Stack gap="xs">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Institute ID / Roll No:</Text>
              <Badge variant="outline" size="lg">{user.institute_id}</Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Account Status:</Text>
              <Badge
                color={user.status === "active" ? "green" : user.status === "deactivated" ? "orange" : "gray"}
                variant="light"
              >
                {user.status.toUpperCase()}
              </Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">User Type:</Text>
              <Text size="sm" fw={600} tt="capitalize">{user.user_type}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Institutional Email:</Text>
              <Text size="sm" fw={500}>{user.institute_email}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Department / Unit:</Text>
              <Text size="sm">{user.department || "—"}</Text>
            </Group>
            {user.user_type === "student" && (
              <>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Programme:</Text>
                  <Text size="sm">{user.programme || "—"}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Discipline:</Text>
                  <Text size="sm">{user.discipline || "—"}</Text>
                </Group>
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">Batch Year:</Text>
                  <Text size="sm">{user.batch_year || "—"}</Text>
                </Group>
              </>
            )}
            {user.user_type !== "student" && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Employee ID:</Text>
                <Text size="sm">{user.employee_id || "—"}</Text>
              </Group>
            )}
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Contact Number:</Text>
              <Text size="sm">{user.contact_number || "—"}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Date of Joining:</Text>
              <Text size="sm">{user.date_of_joining}</Text>
            </Group>
          </Stack>
        </Paper>

        {/* Assigned Roles Card */}
        <Paper withBorder p="md" radius="md">
          <Title order={4} mb="md">Active Additional Roles</Title>
          {user.active_roles.length === 0 ? (
            <Text c="dimmed" size="sm">No additional administrative roles currently held.</Text>
          ) : (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Role</Table.Th>
                  <Table.Th>Scope</Table.Th>
                  <Table.Th>Valid Period</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {user.active_roles.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>
                      <Text size="sm" fw={500}>{r.role_name}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{r.scope || "Institute-wide"}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{r.start_date} to {r.end_date || "Permanent"}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Paper>
      </SimpleGrid>

      {/* Account Lifecycle Timeline */}
      <Paper withBorder p="md" radius="md">
        <Title order={4} mb="md">Account Status Transition History</Title>
        {user.status_history.length === 0 ? (
          <Text c="dimmed" size="sm">No status changes recorded since account initialization.</Text>
        ) : (
          <Timeline active={user.status_history.length - 1} bulletSize={20} lineWidth={2}>
            {user.status_history.map((h) => (
              <Timeline.Item
                key={h.id}
                title={`${h.from_status.toUpperCase()} → ${h.to_status.toUpperCase()}`}
              >
                <Text size="xs" c="dimmed">{new Date(h.changed_at).toLocaleString()}</Text>
                <Text size="sm" mt={4}>
                  <b>Reason:</b> {h.reason}
                </Text>
                <Text size="xs" c="dimmed">
                  <b>Actor:</b> {h.actor_username}
                </Text>
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Paper>

      {/* Modals */}
      <EditUserModal user={user} opened={editOpen} onClose={() => setEditOpen(false)} />
      <ChangeStatusModal
        user={user}
        action={user.status === "active" ? "deactivate" : "reactivate"}
        opened={statusOpen}
        onClose={() => setStatusOpen(false)}
      />
      <ArchiveUserModal opened={archiveOpen} onClose={() => setArchiveOpen(false)} />
    </Stack>
  );
}
