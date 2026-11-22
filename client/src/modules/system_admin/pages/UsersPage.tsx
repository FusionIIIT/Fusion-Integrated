import { useEffect, useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Pagination,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaEdit, FaPlus, FaSearch, FaToggleOff, FaToggleOn } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { adminApi } from "../api/client";
import type { UserAccount, UserType } from "../api/types";

export default function UsersPage() {
  const { can } = useAuth();
  const canAdd = can("system_admin.user.add");
  const canChange = can("system_admin.user.change");

  const [users, setUsers] = useState<UserAccount[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  // Filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Create User Modal
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    institute_id: "",
    username: "",
    email: "",
    user_type: "student" as UserType,
    name: "",
    department: "",
    programme: "",
    discipline: "",
    batch_year: 2024,
  });

  // Edit User Modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserAccount | null>(null);
  const [editName, setEditName] = useState("");
  const [editDepartment, setEditDepartment] = useState("");

  // Deactivate/Reactivate Modal
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [statusAction, setStatusAction] = useState<"deactivate" | "reactivate">("deactivate");
  const [statusReason, setStatusReason] = useState("");

  const fetchUsers = () => {
    setLoading(true);
    adminApi
      .getUsers({
        q: search || undefined,
        user_type: typeFilter || undefined,
        status: statusFilter || undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      })
      .then((res) => {
        setUsers(res.results);
        setTotal(res.total);
      })
      .catch((err) => {
        notifications.show({ color: "red", message: "Failed to load users: " + String(err) });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
  }, [search, typeFilter, statusFilter, page]);

  const handleCreateSubmit = async () => {
    try {
      await adminApi.createUser(createForm);
      notifications.show({ color: "green", message: `User ${createForm.username} created successfully.` });
      setCreateModalOpen(false);
      fetchUsers();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Creation failed: " + String(err) });
    }
  };

  const handleEditSubmit = async () => {
    if (!selectedUser) return;
    try {
      await adminApi.updateUser(selectedUser.user_id, {
        name: editName,
        department: editDepartment,
      });
      notifications.show({ color: "green", message: "Profile updated successfully." });
      setEditModalOpen(false);
      fetchUsers();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Update failed: " + String(err) });
    }
  };

  const handleStatusToggle = async () => {
    if (!selectedUser) return;
    try {
      await adminApi.updateUserStatus(selectedUser.user_id, statusAction, statusReason);
      notifications.show({
        color: "green",
        message: `User ${selectedUser.username} marked as ${statusAction === "deactivate" ? "deactivated" : "active"}.`,
      });
      setStatusModalOpen(false);
      fetchUsers();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Status change failed: " + String(err) });
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="User Identity Management"
        subtitle="Provision and manage student, faculty, and staff user identities with institutional integrity rules."
      />

      <Card withBorder mb="lg" padding="md">
        <Group justify="space-between" wrap="wrap">
          <Group gap="sm">
            <TextInput
              placeholder="Search by ID, username, name..."
              leftSection={<FaSearch size={14} />}
              value={search}
              onChange={(e) => {
                setSearch(e.currentTarget.value);
                setPage(1);
              }}
              w={260}
            />
            <Select
              placeholder="User Type"
              data={[
                { value: "student", label: "Students" },
                { value: "faculty", label: "Faculty" },
                { value: "staff", label: "Staff" },
              ]}
              value={typeFilter}
              onChange={(val) => {
                setTypeFilter(val);
                setPage(1);
              }}
              clearable
              w={140}
            />
            <Select
              placeholder="Status"
              data={[
                { value: "active", label: "Active" },
                { value: "deactivated", label: "Deactivated" },
                { value: "archived", label: "Archived" },
              ]}
              value={statusFilter}
              onChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
              clearable
              w={140}
            />
          </Group>

          {canAdd && (
            <Button leftSection={<FaPlus />} onClick={() => setCreateModalOpen(true)}>
              Create Basic User
            </Button>
          )}
        </Group>
      </Card>

      <Card withBorder padding="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Institute ID</Table.Th>
              <Table.Th>Username</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Department / Programme</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((u) => (
              <Table.Tr key={u.user_id}>
                <Table.Td fw={500}>{u.institute_id}</Table.Td>
                <Table.Td>{u.username}</Table.Td>
                <Table.Td>{u.name || "—"}</Table.Td>
                <Table.Td>
                  <Badge variant="outline" color={u.user_type === "student" ? "blue" : "teal"}>
                    {u.user_type}
                  </Badge>
                </Table.Td>
                <Table.Td>{u.department || `${u.programme} (${u.discipline})` || "—"}</Table.Td>
                <Table.Td>
                  <Badge color={u.status === "active" ? "green" : u.status === "deactivated" ? "orange" : "gray"}>
                    {u.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {canChange && (
                      <ActionIcon
                        variant="subtle"
                        color="blue"
                        title="Edit Profile"
                        onClick={() => {
                          setSelectedUser(u);
                          setEditName(u.name);
                          setEditDepartment(u.department);
                          setEditModalOpen(true);
                        }}
                      >
                        <FaEdit size={14} />
                      </ActionIcon>
                    )}
                    {canChange && u.status === "active" && (
                      <ActionIcon
                        variant="subtle"
                        color="orange"
                        title="Deactivate Account"
                        onClick={() => {
                          setSelectedUser(u);
                          setStatusAction("deactivate");
                          setStatusReason("");
                          setStatusModalOpen(true);
                        }}
                      >
                        <FaToggleOff size={14} />
                      </ActionIcon>
                    )}
                    {canChange && u.status === "deactivated" && (
                      <ActionIcon
                        variant="subtle"
                        color="green"
                        title="Reactivate Account"
                        onClick={() => {
                          setSelectedUser(u);
                          setStatusAction("reactivate");
                          setStatusReason("");
                          setStatusModalOpen(true);
                        }}
                      >
                        <FaToggleOn size={14} />
                      </ActionIcon>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
            {users.length === 0 && !loading && (
              <Table.Tr>
                <Table.Td colSpan={7} style={{ textAlign: "center", padding: "2rem" }}>
                  <Text c="dimmed">No users matching search criteria.</Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>

        {total > pageSize && (
          <Group justify="center" mt="md">
            <Pagination total={Math.ceil(total / pageSize)} value={page} onChange={setPage} />
          </Group>
        )}
      </Card>

      {/* Create User Modal */}
      <Modal opened={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Create Basic User Account" size="lg">
        <Stack gap="sm">
          <TextInput
            label="Institute ID (Immutable once set)"
            required
            placeholder="e.g. 2024BCS050 or FAC101"
            value={createForm.institute_id}
            onChange={(e) => setCreateForm({ ...createForm, institute_id: e.currentTarget.value })}
          />
          <TextInput
            label="Username"
            required
            placeholder="e.g. jdoe"
            value={createForm.username}
            onChange={(e) => setCreateForm({ ...createForm, username: e.currentTarget.value })}
          />
          <TextInput
            label="Institute Email (@iiitdmj.ac.in mandatory)"
            required
            placeholder="e.g. jdoe@iiitdmj.ac.in"
            value={createForm.email}
            onChange={(e) => setCreateForm({ ...createForm, email: e.currentTarget.value })}
          />
          <Select
            label="User Type"
            data={[
              { value: "student", label: "Student" },
              { value: "faculty", label: "Faculty" },
              { value: "staff", label: "Staff" },
            ]}
            value={createForm.user_type}
            onChange={(val) => setCreateForm({ ...createForm, user_type: (val as UserType) || "student" })}
          />
          <TextInput
            label="Full Name"
            placeholder="e.g. Jane Doe"
            value={createForm.name}
            onChange={(e) => setCreateForm({ ...createForm, name: e.currentTarget.value })}
          />
          {createForm.user_type === "student" ? (
            <>
              <TextInput
                label="Programme"
                placeholder="e.g. B.Tech"
                value={createForm.programme}
                onChange={(e) => setCreateForm({ ...createForm, programme: e.currentTarget.value })}
              />
              <TextInput
                label="Discipline"
                placeholder="e.g. CSE"
                value={createForm.discipline}
                onChange={(e) => setCreateForm({ ...createForm, discipline: e.currentTarget.value })}
              />
            </>
          ) : (
            <TextInput
              label="Department"
              placeholder="e.g. Computer Science and Engineering"
              value={createForm.department}
              onChange={(e) => setCreateForm({ ...createForm, department: e.currentTarget.value })}
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateSubmit}>Create Account</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Edit Profile Modal */}
      <Modal opened={editModalOpen} onClose={() => setEditModalOpen(false)} title="Update User Profile">
        <Stack gap="sm">
          <Text size="sm" c="dimmed">
            Institute ID: <b>{selectedUser?.institute_id}</b> (Immutable)
          </Text>
          <TextInput label="Full Name" value={editName} onChange={(e) => setEditName(e.currentTarget.value)} />
          <TextInput
            label="Department"
            value={editDepartment}
            onChange={(e) => setEditDepartment(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setEditModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleEditSubmit}>Save Changes</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Deactivate/Reactivate Modal */}
      <Modal
        opened={statusModalOpen}
        onClose={() => setStatusModalOpen(false)}
        title={`${statusAction === "deactivate" ? "Deactivate" : "Reactivate"} User Account`}
      >
        <Stack gap="sm">
          <Text size="sm">
            Are you sure you want to {statusAction} account for <b>{selectedUser?.username}</b> ({selectedUser?.institute_id})?
          </Text>
          <TextInput
            label="Reason for status change"
            required
            placeholder="e.g. Program completion or academic resumption"
            value={statusReason}
            onChange={(e) => setStatusReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setStatusModalOpen(false)}>
              Cancel
            </Button>
            <Button color={statusAction === "deactivate" ? "orange" : "green"} onClick={handleStatusToggle}>
              Confirm {statusAction === "deactivate" ? "Deactivation" : "Reactivation"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
