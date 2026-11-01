import { useState } from "react";
import {
  Stack,
  Group,
  TextInput,
  Select,
  Button,
  Badge,
  ActionIcon,
  Menu,
  Table,
  Paper,
  Text,
  Loader,
  Alert,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { FaEllipsisV, FaEdit, FaUserSlash, FaUserCheck, FaEye, FaUpload, FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useUsers } from "../api/hooks";
import type { BasicUser } from "../api/types";
import { CreateUserModal, EditUserModal, ChangeStatusModal, BulkCreateModal } from "../components/UserModals";

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [userType, setUserType] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");

  const [createOpen, setCreateOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<BasicUser | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [statusAction, setStatusAction] = useState<"deactivate" | "reactivate">("deactivate");

  const filters = {
    search: search || undefined,
    user_type: userType !== "all" ? userType : undefined,
    status: status !== "all" ? status : undefined,
  };

  const { data, isLoading, error } = useUsers(filters);

  const handleEdit = (u: BasicUser) => {
    setSelectedUser(u);
    setEditOpen(true);
  };

  const handleStatusChange = (u: BasicUser, act: "deactivate" | "reactivate") => {
    setSelectedUser(u);
    setStatusAction(act);
    setStatusOpen(true);
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Basic User Directory"
        subtitle="Manage student, faculty, and staff institutional identity records"
        action={
          <Group gap="sm">
            <Button variant="default" leftSection={<FaUpload size={14} />} onClick={() => setBulkOpen(true)}>
              Bulk Import CSV
            </Button>
            <Button leftSection={<FaPlus size={14} />} onClick={() => setCreateOpen(true)}>
              Create User
            </Button>
          </Group>
        }
      />

      {/* Filter and Search Bar */}
      <Paper withBorder p="md" radius="md">
        <Group grow wrap="wrap">
          <TextInput
            placeholder="Search by Roll No, Name, or Email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select
            label="User Type"
            data={[
              { value: "all", label: "All User Types" },
              { value: "student", label: "Students" },
              { value: "faculty", label: "Faculty" },
              { value: "staff", label: "Staff" },
            ]}
            value={userType}
            onChange={(val) => setUserType(val ?? "all")}
          />
          <Select
            label="Account Status"
            data={[
              { value: "all", label: "All Account Statuses" },
              { value: "active", label: "Active" },
              { value: "deactivated", label: "Deactivated" },
              { value: "archived", label: "Archived" },
            ]}
            value={status}
            onChange={(val) => setStatus(val ?? "all")}
          />
        </Group>
      </Paper>

      {/* Users Table */}
      {isLoading && (
        <Stack align="center" justify="center" p="xl">
          <Loader />
          <Text c="dimmed">Loading user directory...</Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error">
          Failed to load users.
        </Alert>
      )}

      {data && (
        <Paper withBorder radius="md">
          <Table verticalSpacing="sm" striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Institute ID</Table.Th>
                <Table.Th>Full Name</Table.Th>
                <Table.Th>Type</Table.Th>
                <Table.Th>Department / Academic Unit</Table.Th>
                <Table.Th>Institutional Email</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data.results.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    <Text c="dimmed" p="md">No basic user profiles found matching criteria.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                data.results.map((u) => (
                  <Table.Tr key={u.id}>
                    <Table.Td>
                      <Text
                        component={Link}
                        to={`/systemadmin/users/${u.id}`}
                        fw={600}
                        c="blue"
                        style={{ textDecoration: "none" }}
                      >
                        {u.institute_id}
                      </Text>
                    </Table.Td>
                    <Table.Td>{u.full_name}</Table.Td>
                    <Table.Td>
                      <Badge
                        variant="light"
                        color={u.user_type === "faculty" ? "grape" : u.user_type === "staff" ? "orange" : "blue"}
                      >
                        {u.user_type}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{u.department || u.programme || "—"}</Table.Td>
                    <Table.Td>{u.institute_email}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={u.status === "active" ? "green" : u.status === "deactivated" ? "orange" : "gray"}
                        variant="light"
                      >
                        {u.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td style={{ textAlign: "right" }}>
                      <Menu position="bottom-end" shadow="md">
                        <Menu.Target>
                          <ActionIcon variant="subtle"><FaEllipsisV size={14} /></ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          <Menu.Item
                            component={Link}
                            to={`/systemadmin/users/${u.id}`}
                            leftSection={<FaEye size={14} />}
                          >
                            View Full Profile
                          </Menu.Item>
                          <Menu.Item
                            leftSection={<FaEdit size={14} />}
                            onClick={() => handleEdit(u)}
                            disabled={u.status === "archived"}
                          >
                            Edit Profile
                          </Menu.Item>
                          {u.status === "active" ? (
                            <Menu.Item
                              leftSection={<FaUserSlash size={14} />}
                              color="red"
                              onClick={() => handleStatusChange(u, "deactivate")}
                            >
                              Deactivate
                            </Menu.Item>
                          ) : u.status === "deactivated" ? (
                            <Menu.Item
                              leftSection={<FaUserCheck size={14} />}
                              color="green"
                              onClick={() => handleStatusChange(u, "reactivate")}
                            >
                              Reactivate
                            </Menu.Item>
                          ) : null}
                        </Menu.Dropdown>
                      </Menu>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      {/* Modals */}
      <CreateUserModal opened={createOpen} onClose={() => setCreateOpen(false)} />
      <BulkCreateModal opened={bulkOpen} onClose={() => setBulkOpen(false)} />
      {selectedUser && (
        <>
          <EditUserModal
            user={selectedUser}
            opened={editOpen}
            onClose={() => {
              setEditOpen(false);
              setSelectedUser(null);
            }}
          />
          <ChangeStatusModal
            user={selectedUser}
            action={statusAction}
            opened={statusOpen}
            onClose={() => {
              setStatusOpen(false);
              setSelectedUser(null);
            }}
          />
        </>
      )}
    </Stack>
  );
}
