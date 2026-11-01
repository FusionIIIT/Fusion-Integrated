import { useState } from "react";
import {
  Stack,
  Table,
  Badge,
  Text,
  Button,
  Paper,
  Group,
  Loader,
  Alert,
  Select,
  TextInput,
  Menu,
  ActionIcon,
} from "@mantine/core";
import {
  FaUserPlus,
  FaEllipsisV,
  FaExchangeAlt,
  FaBan,
  FaCalendarPlus,
  FaSearch,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRoleAssignments, useRoles } from "../api/hooks";
import type { RoleAssignmentItem } from "../api/types";
import {
  AssignRoleModal,
  ReassignRoleModal,
  RevokeRoleModal,
  ExtendRoleModal,
} from "../components/RoleModals";

export default function RoleAssignmentsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState("");

  const { data: rolesData } = useRoles();
  const { data: assignmentsData, isLoading, error } = useRoleAssignments(
    statusFilter === "all" ? undefined : { status: statusFilter }
  );

  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedAssignment, setSelectedAssignment] = useState<RoleAssignmentItem | null>(null);
  const [reassignOpen, setReassignOpen] = useState(false);
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [extendOpen, setExtendOpen] = useState(false);

  const assignments = (assignmentsData?.results ?? []).filter((a) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      a.role_details?.name?.toLowerCase().includes(term) ||
      a.role_details?.code?.toLowerCase().includes(term) ||
      a.user_details?.full_name?.toLowerCase().includes(term) ||
      a.user_details?.institute_id?.toLowerCase().includes(term)
    );
  });

  const getStatusBadge = (status: RoleAssignmentItem["status"]) => {
    switch (status) {
      case "active":
        return <Badge color="green">Active</Badge>;
      case "scheduled":
        return <Badge color="blue">Scheduled</Badge>;
      case "extended":
        return <Badge color="teal">Extended</Badge>;
      case "expired":
        return <Badge color="gray">Expired</Badge>;
      case "reassigned":
        return <Badge color="orange">Reassigned</Badge>;
      case "revoked":
        return <Badge color="red">Revoked</Badge>;
      default:
        return <Badge color="gray">{status}</Badge>;
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Role Assignments"
        subtitle="Manage active tenures, scheduled appointments, extensions, handovers, and revocations"
        action={
          <Button
            leftSection={<FaUserPlus size={14} />}
            onClick={() => setAssignOpen(true)}
            disabled={!rolesData || rolesData.results.length === 0}
          >
            Assign Role
          </Button>
        }
      />

      {/* Filter Toolbar */}
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between">
          <Group>
            <TextInput
              leftSection={<FaSearch size={14} />}
              placeholder="Search user, ID, or role..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.currentTarget.value)}
              w={260}
            />
            <Select
              placeholder="Filter by Status"
              data={[
                { value: "all", label: "All Statuses" },
                { value: "active", label: "Active" },
                { value: "scheduled", label: "Scheduled" },
                { value: "extended", label: "Extended" },
                { value: "expired", label: "Expired" },
                { value: "reassigned", label: "Reassigned" },
                { value: "revoked", label: "Revoked" },
              ]}
              value={statusFilter}
              onChange={(val) => setStatusFilter(val ?? "all")}
              w={180}
            />
          </Group>
          <Text size="sm" c="dimmed">
            Showing {assignments.length} assignments
          </Text>
        </Group>
      </Paper>

      {isLoading && (
        <Stack align="center" justify="center" p="xl">
          <Loader />
          <Text c="dimmed">Loading assignments...</Text>
        </Stack>
      )}

      {error && (
        <Alert color="red" title="Error">
          Failed to load role assignments.
        </Alert>
      )}

      {assignmentsData && (
        <Paper withBorder radius="md">
          <Table verticalSpacing="sm" striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Role</Table.Th>
                <Table.Th>Assigned Holder</Table.Th>
                <Table.Th>Scope / Dept</Table.Th>
                <Table.Th>Tenure Period</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th style={{ width: 80, textAlign: "center" }}>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {assignments.map((assignment) => {
                const canModify = ["active", "scheduled", "extended"].includes(assignment.status);
                return (
                  <Table.Tr key={assignment.id}>
                    <Table.Td>
                      <Text fw={600}>{assignment.role_details?.name}</Text>
                      <Text size="xs" c="dimmed">
                        {assignment.role_details?.code} {assignment.role_details?.is_singular ? "• Singular" : ""}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={500}>{assignment.user_details?.full_name}</Text>
                      <Text size="xs" c="dimmed">
                        {assignment.user_details?.institute_id} ({assignment.user_details?.user_type})
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{assignment.scope || assignment.role_details?.module_or_dept || "Institute-wide"}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {assignment.start_date} → {assignment.end_date ?? "Indefinite"}
                      </Text>
                    </Table.Td>
                    <Table.Td>{getStatusBadge(assignment.status)}</Table.Td>
                    <Table.Td style={{ textAlign: "center" }}>
                      {canModify ? (
                        <Menu position="bottom-end" withArrow>
                          <Menu.Target>
                            <ActionIcon variant="subtle" color="gray">
                              <FaEllipsisV size={14} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              leftSection={<FaExchangeAlt size={13} />}
                              onClick={() => {
                                setSelectedAssignment(assignment);
                                setReassignOpen(true);
                              }}
                            >
                              Reassign / Handover
                            </Menu.Item>
                            <Menu.Item
                              leftSection={<FaCalendarPlus size={13} />}
                              onClick={() => {
                                setSelectedAssignment(assignment);
                                setExtendOpen(true);
                              }}
                            >
                              Extend Validity
                            </Menu.Item>
                            <Menu.Divider />
                            <Menu.Item
                              color="red"
                              leftSection={<FaBan size={13} />}
                              onClick={() => {
                                setSelectedAssignment(assignment);
                                setRevokeOpen(true);
                              }}
                            >
                              Revoke Early
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      ) : (
                        <Text size="xs" c="dimmed">—</Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                );
              })}
              {assignments.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">No assignments found matching criteria.</Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Paper>
      )}

      {/* Modals */}
      {rolesData && (
        <AssignRoleModal
          roles={rolesData.results}
          opened={assignOpen}
          onClose={() => setAssignOpen(false)}
        />
      )}

      {selectedAssignment && (
        <>
          <ReassignRoleModal
            assignment={selectedAssignment}
            opened={reassignOpen}
            onClose={() => {
              setReassignOpen(false);
              setSelectedAssignment(null);
            }}
          />
          <RevokeRoleModal
            assignment={selectedAssignment}
            opened={revokeOpen}
            onClose={() => {
              setRevokeOpen(false);
              setSelectedAssignment(null);
            }}
          />
          <ExtendRoleModal
            assignment={selectedAssignment}
            opened={extendOpen}
            onClose={() => {
              setExtendOpen(false);
              setSelectedAssignment(null);
            }}
          />
        </>
      )}
    </Stack>
  );
}
