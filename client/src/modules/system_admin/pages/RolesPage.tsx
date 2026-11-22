import { useEffect, useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExchangeAlt, FaHistory, FaPlus, FaTimesCircle } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { adminApi } from "../api/client";
import type { RoleAssignment, RoleDirectoryEntry } from "../api/types";

export default function RolesPage() {
  const { can } = useAuth();
  const canManage = can("system_admin.role.manage");

  const [activeTab, setActiveTab] = useState<string | null>("directory");
  const [directory, setDirectory] = useState<RoleDirectoryEntry[]>([]);
  const [assignments, setAssignments] = useState<RoleAssignment[]>([]);

  // Assign Modal
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({
    role_code: "",
    user_id: "",
    start_date: new Date().toISOString().slice(0, 10),
    end_date: "",
    scope: "",
    reason: "",
    is_singular: false,
  });

  // Reassign Modal
  const [reassignModalOpen, setReassignModalOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<RoleAssignment | null>(null);
  const [newUserId, setNewUserId] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [reassignReason, setReassignReason] = useState("");

  // Extend Modal
  const [extendModalOpen, setExtendModalOpen] = useState(false);
  const [newEndDate, setNewEndDate] = useState("");
  const [extendReason, setExtendReason] = useState("");

  // Revoke Modal
  const [revokeModalOpen, setRevokeModalOpen] = useState(false);
  const [revokeReason, setRevokeReason] = useState("");
  const [isEmergency, setIsEmergency] = useState(false);

  const fetchData = () => {
    Promise.all([adminApi.getRoleDirectory(), adminApi.getRoles()])
      .then(([dirData, assignData]) => {
        setDirectory(dirData);
        setAssignments(assignData);
      })
      .catch((err) => {
        notifications.show({ color: "red", message: "Failed to load roles: " + String(err) });
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAssignSubmit = async () => {
    try {
      await adminApi.assignRole({
        role_code: assignForm.role_code,
        user_id: parseInt(assignForm.user_id, 10),
        start_date: assignForm.start_date,
        end_date: assignForm.end_date || null,
        scope: assignForm.scope,
        reason: assignForm.reason,
        is_singular: assignForm.is_singular,
      });
      notifications.show({ color: "green", message: `Role ${assignForm.role_code} assigned successfully.` });
      setAssignModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Role assignment failed: " + String(err) });
    }
  };

  const handleReassignSubmit = async () => {
    if (!selectedRole) return;
    try {
      await adminApi.reassignRole(selectedRole.id, {
        new_user_id: parseInt(newUserId, 10),
        effective_date: effectiveDate,
        reason: reassignReason,
      });
      notifications.show({ color: "green", message: "Role reassigned successfully." });
      setReassignModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Reassignment failed: " + String(err) });
    }
  };

  const handleExtendSubmit = async () => {
    if (!selectedRole) return;
    try {
      await adminApi.extendRole(selectedRole.id, newEndDate, extendReason);
      notifications.show({ color: "green", message: "Role validity extended successfully." });
      setExtendModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Extension failed: " + String(err) });
    }
  };

  const handleRevokeSubmit = async () => {
    if (!selectedRole) return;
    try {
      await adminApi.revokeRole(selectedRole.id, revokeReason, isEmergency);
      notifications.show({ color: "green", message: "Role revoked successfully." });
      setRevokeModalOpen(false);
      fetchData();
    } catch (err: unknown) {
      notifications.show({ color: "red", message: "Revocation failed: " + String(err) });
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Institutional Role Directory & Governance"
        subtitle="Manage singular key positions, time-bound roles, separation of duties, and transitions."
      />

      <Card withBorder mb="lg" padding="md">
        <Group justify="space-between">
          <Text fw={600} size="lg">
            Role Operations
          </Text>
          {canManage && (
            <Button leftSection={<FaPlus />} onClick={() => setAssignModalOpen(true)}>
              Assign Additional Role
            </Button>
          )}
        </Group>
      </Card>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="directory">Role Directory & Availability</Tabs.Tab>
          <Tabs.Tab value="assignments">Active Role Assignments ({assignments.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="directory">
          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Role Title</Table.Th>
                  <Table.Th>Role Code</Table.Th>
                  <Table.Th>Structure</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Active Holders</Table.Th>
                  <Table.Th>Availability Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {directory.map((r) => (
                  <Table.Tr key={r.role_code}>
                    <Table.Td fw={500}>{r.role_name}</Table.Td>
                    <Table.Td>{r.role_code}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline" color={r.is_singular ? "violet" : "blue"}>
                        {r.is_singular ? "Singular (1-to-1)" : "Multi-Holder"}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{r.category}</Table.Td>
                    <Table.Td>{r.active_holders_count}</Table.Td>
                    <Table.Td>
                      {r.is_vacant ? (
                        <Badge color="red">Vacant</Badge>
                      ) : (
                        <Badge color="green">Occupied ({r.active_holders_count})</Badge>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="assignments">
          <Card withBorder padding="md">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Role</Table.Th>
                  <Table.Th>User ID</Table.Th>
                  <Table.Th>Start Date</Table.Th>
                  <Table.Th>End Date</Table.Th>
                  <Table.Th>Scope</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {assignments.map((a) => (
                  <Table.Tr key={a.id}>
                    <Table.Td fw={500}>{a.role_name || a.role_code}</Table.Td>
                    <Table.Td>{a.user_id}</Table.Td>
                    <Table.Td>{a.start_date}</Table.Td>
                    <Table.Td>{a.end_date || "Permanent"}</Table.Td>
                    <Table.Td>{a.scope || "Institutional"}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={
                          a.status === "active"
                            ? "green"
                            : a.status === "scheduled"
                            ? "blue"
                            : a.status === "expired"
                            ? "orange"
                            : "gray"
                        }
                      >
                        {a.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {canManage && a.status === "active" && (
                        <Group gap="xs">
                          <ActionIcon
                            variant="subtle"
                            color="blue"
                            title="Reassign Role"
                            onClick={() => {
                              setSelectedRole(a);
                              setNewUserId("");
                              setReassignReason("");
                              setReassignModalOpen(true);
                            }}
                          >
                            <FaExchangeAlt size={14} />
                          </ActionIcon>
                          <ActionIcon
                            variant="subtle"
                            color="teal"
                            title="Extend Validity"
                            onClick={() => {
                              setSelectedRole(a);
                              setNewEndDate(a.end_date || "");
                              setExtendReason("");
                              setExtendModalOpen(true);
                            }}
                          >
                            <FaHistory size={14} />
                          </ActionIcon>
                          <ActionIcon
                            variant="subtle"
                            color="red"
                            title="Revoke Role"
                            onClick={() => {
                              setSelectedRole(a);
                              setRevokeReason("");
                              setIsEmergency(false);
                              setRevokeModalOpen(true);
                            }}
                          >
                            <FaTimesCircle size={14} />
                          </ActionIcon>
                        </Group>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Assign Role Modal */}
      <Modal opened={assignModalOpen} onClose={() => setAssignModalOpen(false)} title="Assign Role to User" size="md">
        <Stack gap="sm">
          <Select
            label="Role Code"
            required
            placeholder="Select Role"
            data={directory.map((d) => ({ value: d.role_code, label: `${d.role_name} (${d.role_code})` }))}
            value={assignForm.role_code}
            onChange={(val) => {
              const item = directory.find((d) => d.role_code === val);
              setAssignForm({
                ...assignForm,
                role_code: val || "",
                is_singular: item ? item.is_singular : false,
              });
            }}
          />
          <TextInput
            label="Target User ID"
            required
            placeholder="e.g. 5001"
            value={assignForm.user_id}
            onChange={(e) => setAssignForm({ ...assignForm, user_id: e.currentTarget.value })}
          />
          <TextInput
            label="Start Date"
            type="date"
            required
            value={assignForm.start_date}
            onChange={(e) => setAssignForm({ ...assignForm, start_date: e.currentTarget.value })}
          />
          <TextInput
            label="End Date (Optional)"
            type="date"
            value={assignForm.end_date}
            onChange={(e) => setAssignForm({ ...assignForm, end_date: e.currentTarget.value })}
          />
          <TextInput
            label="Scope / Department"
            placeholder="e.g. CSE or Institutional"
            value={assignForm.scope}
            onChange={(e) => setAssignForm({ ...assignForm, scope: e.currentTarget.value })}
          />
          <TextInput
            label="Reason for Assignment"
            placeholder="e.g. Appointed by Board of Governors"
            value={assignForm.reason}
            onChange={(e) => setAssignForm({ ...assignForm, reason: e.currentTarget.value })}
          />
          <Checkbox
            label="Mark as Singular Role (Disallows overlapping active holders)"
            checked={assignForm.is_singular}
            onChange={(e) => setAssignForm({ ...assignForm, is_singular: e.currentTarget.checked })}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAssignModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAssignSubmit}>Assign Role</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reassign Modal */}
      <Modal opened={reassignModalOpen} onClose={() => setReassignModalOpen(false)} title="Reassign Role">
        <Stack gap="sm">
          <Text size="sm">
            Reassigning <b>{selectedRole?.role_name || selectedRole?.role_code}</b> currently held by user{" "}
            <b>{selectedRole?.user_id}</b>.
          </Text>
          <TextInput
            label="New Holder User ID"
            required
            placeholder="e.g. 5002"
            value={newUserId}
            onChange={(e) => setNewUserId(e.currentTarget.value)}
          />
          <TextInput
            label="Effective Date"
            type="date"
            required
            value={effectiveDate}
            onChange={(e) => setEffectiveDate(e.currentTarget.value)}
          />
          <TextInput
            label="Reason for Reassignment"
            required
            placeholder="e.g. Routine tenure handover"
            value={reassignReason}
            onChange={(e) => setReassignReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setReassignModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleReassignSubmit}>Confirm Reassignment</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Extend Modal */}
      <Modal opened={extendModalOpen} onClose={() => setExtendModalOpen(false)} title="Extend Role Validity">
        <Stack gap="sm">
          <Text size="sm">
            Extending tenure for <b>{selectedRole?.role_name}</b> (Current end: {selectedRole?.end_date || "None"}).
          </Text>
          <TextInput
            label="New End Date"
            type="date"
            required
            value={newEndDate}
            onChange={(e) => setNewEndDate(e.currentTarget.value)}
          />
          <TextInput
            label="Reason for Extension"
            required
            placeholder="e.g. Extension authorized pending committee review"
            value={extendReason}
            onChange={(e) => setExtendReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setExtendModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleExtendSubmit}>Save Extension</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Revoke Modal */}
      <Modal opened={revokeModalOpen} onClose={() => setRevokeModalOpen(false)} title="Revoke Role Assignment">
        <Stack gap="sm">
          <Text size="sm" c="red">
            Are you sure you want to revoke <b>{selectedRole?.role_name}</b> from user <b>{selectedRole?.user_id}</b>?
          </Text>
          <TextInput
            label="Reason for Revocation"
            required
            placeholder="e.g. Resignation or duty conclusion"
            value={revokeReason}
            onChange={(e) => setRevokeReason(e.currentTarget.value)}
          />
          <Checkbox
            label="Emergency Immediate Revocation (Suspends all active sessions immediately)"
            checked={isEmergency}
            onChange={(e) => setIsEmergency(e.currentTarget.checked)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRevokeModalOpen(false)}>
              Cancel
            </Button>
            <Button color="red" onClick={handleRevokeSubmit}>
              Revoke Role
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
