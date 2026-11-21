import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { FaFileImport, FaPlus, FaSearch, FaUsers } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useUsers } from "../api/hooks";
import type { AdminUser } from "../api/types";
import { BulkUserModal } from "../components/BulkUserModal";
import { CreateUserModal } from "../components/CreateUserModal";
import { UserDetailsDrawer } from "../components/UserDetailsDrawer";

const KIND_OPTIONS = [
  { value: "", label: "All Classifications" },
  { value: "student", label: "Students" },
  { value: "faculty", label: "Faculty" },
  { value: "staff", label: "Staff" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "deactivated", label: "Deactivated" },
  { value: "archived", label: "Archived" },
];

export default function UsersPage() {
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<string | null>("");
  const [status, setStatus] = useState<string | null>("");

  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [creatingUser, setCreatingUser] = useState(false);
  const [bulkImporting, setBulkImporting] = useState(false);

  const { data, isPending, error } = useUsers({
    search: search.trim() || undefined,
    kind: kind || undefined,
    status: status || undefined,
  });

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const rawUsers = Array.isArray(data)
    ? data
    : Array.isArray(data?.results)
    ? data.results
    : [];

  return (
    <Container size="xl">
      <PageHeader
        title="User Accounts"
        subtitle="Manage institute identities, department placements, and lifecycle statuses"
        action={
          <Group gap="xs">
            <Button
              variant="default"
              leftSection={<FaFileImport size={12} />}
              onClick={() => setBulkImporting(true)}
            >
              Bulk Import
            </Button>
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setCreatingUser(true)}
            >
              New User
            </Button>
          </Group>
        }
      />

      <Card padding="md" mb="md" withBorder radius="md">
        <Group>
          <TextInput
            placeholder="Search by name, institute ID, or email..."
            leftSection={<FaSearch size={12} />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Select
            placeholder="User Kind"
            data={KIND_OPTIONS}
            value={kind}
            onChange={setKind}
            clearable
          />
          <Select
            placeholder="Status"
            data={STATUS_OPTIONS}
            value={status}
            onChange={setStatus}
            clearable
          />
        </Group>
      </Card>

      <Card padding="lg" withBorder radius="md">
        <DataTable<AdminUser>
          rows={rawUsers}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          columns={[
            {
              key: "name",
              header: "User / Account",
              render: (r) => (
                <Stack gap={0}>
                  <Text
                    fw={600}
                    style={{ cursor: "pointer", color: "#1971c2" }}
                    onClick={() => setSelectedUser(r)}
                  >
                    {r.profile?.display_name || r.username}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.email}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "institute_id",
              header: "Institute ID",
              render: (r) => (
                <Text size="sm" fw={500}>
                  {r.institute_id}
                </Text>
              ),
            },
            {
              key: "kind",
              header: "Type",
              render: (r) => (
                <Badge
                  variant="outline"
                  size="sm"
                  color={
                    r.kind === "student"
                      ? "blue"
                      : r.kind === "faculty"
                      ? "violet"
                      : "teal"
                  }
                >
                  {r.kind}
                </Badge>
              ),
            },
            {
              key: "department",
              header: "Department",
              render: (r) => (
                <Text size="sm">{r.profile?.department || "—"}</Text>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "actions",
              header: "",
              align: "right",
              render: (r) => (
                <Button
                  size="xs"
                  variant="subtle"
                  onClick={() => setSelectedUser(r)}
                >
                  Manage
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaUsers,
            title: "No Users Found",
            description: "No user accounts matched the given search and filter criteria.",
          }}
        />
      </Card>

      <UserDetailsDrawer
        user={selectedUser}
        opened={Boolean(selectedUser)}
        onClose={() => setSelectedUser(null)}
      />

      <CreateUserModal
        opened={creatingUser}
        onClose={() => setCreatingUser(false)}
      />

      <BulkUserModal
        opened={bulkImporting}
        onClose={() => setBulkImporting(false)}
      />
    </Container>
  );
}
