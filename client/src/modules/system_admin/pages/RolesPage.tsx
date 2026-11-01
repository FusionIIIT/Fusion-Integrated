import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  FaCalendarAlt,
  FaCheck,
  FaExchangeAlt,
  FaHistory,
  FaIdBadge,
  FaPlus,
  FaTimes,
  FaUserMinus,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAssignRole,
  useExtendRole,
  useReassignRole,
  useRevokeRole,
  useRoleAssignments,
  useRoleDefinitions,
  useRoleVacancies,
} from "../api/hooks";
import type { RoleAssignment } from "../api/types";

export default function RolesPage() {
  const [filterModule, setFilterModule] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);

  const { data: roleDefs = [] } = useRoleDefinitions(filterModule || undefined);
  const { data: vacancies = [] } = useRoleVacancies();
  const { data: assignments = [] } = useRoleAssignments({
    status: filterStatus || undefined,
  });

  const assignMutation = useAssignRole();
  const reassignMutation = useReassignRole();
  const revokeMutation = useRevokeRole();
  const extendMutation = useExtendRole();

  // Assign Role Modal state
  const [assignOpened, { open: openAssign, close: closeAssign }] = useDisclosure(false);
  const [assignUserId, setAssignUserId] = useState<number | "">("");
  const [assignRoleCode, setAssignRoleCode] = useState("");
  const [assignStartDate, setAssignStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [assignEndDate, setAssignEndDate] = useState("");
  const [assignScopeType, setAssignScopeType] = useState("institute");
  const [assignScopeId, setAssignScopeId] = useState("");
  const [assignReason, setAssignReason] = useState("");

  // Reassign Modal state
  const [reassignAssignment, setReassignAssignment] = useState<RoleAssignment | null>(null);
  const [reassignNewUserId, setReassignNewUserId] = useState<number | "">("");
  const [reassignEffectiveDate, setReassignEffectiveDate] = useState(new Date().toISOString().split("T")[0]);
  const [reassignReason, setReassignReason] = useState("");
  const [reassignAuditDays, setReassignAuditDays] = useState<number | "">(30);

  // Revoke Modal state
  const [revokeAssignment, setRevokeAssignment] = useState<RoleAssignment | null>(null);
  const [revokeEffectiveDate, setRevokeEffectiveDate] = useState(
    new Date(Date.now() + 86400000).toISOString().split("T")[0]
  );
  const [revokeReason, setRevokeReason] = useState("");
  const [revokeEmergency, setRevokeEmergency] = useState(false);
  const [revokeDisposition, setRevokeDisposition] = useState<"transfer" | "close">("transfer");

  // Extend Modal state
  const [extendAssignment, setExtendAssignment] = useState<RoleAssignment | null>(null);
  const [extendEndDate, setExtendEndDate] = useState("");
  const [extendReason, setExtendReason] = useState("");

  const handleAssign = async () => {
    if (!assignUserId || !assignRoleCode || !assignStartDate) return;
    try {
      await assignMutation.mutateAsync({
        user_id: Number(assignUserId),
        role_code: assignRoleCode,
        start_date: assignStartDate,
        end_date: assignEndDate || undefined,
        scope_type: assignScopeType,
        scope_id: assignScopeId,
        reason: assignReason,
      });
      closeAssign();
      setAssignUserId("");
      setAssignRoleCode("");
      setAssignReason("");
    } catch {
      // Error handled
    }
  };

  const handleReassign = async () => {
    if (!reassignAssignment || !reassignNewUserId || !reassignEffectiveDate || !reassignReason) return;
    try {
      await reassignMutation.mutateAsync({
        assignmentId: reassignAssignment.id,
        new_user_id: Number(reassignNewUserId),
        effective_date: reassignEffectiveDate,
        reason: reassignReason,
        audit_access_days: typeof reassignAuditDays === "number" ? reassignAuditDays : 30,
      });
      setReassignAssignment(null);
    } catch {
      // Error handled
    }
  };

  const handleRevoke = async () => {
    if (!revokeAssignment || !revokeEffectiveDate || !revokeReason) return;
    try {
      await revokeMutation.mutateAsync({
        assignmentId: revokeAssignment.id,
        effective_date: revokeEffectiveDate,
        reason: revokeReason,
        pending_task_disposition: revokeDisposition,
        is_emergency: revokeEmergency,
      });
      setRevokeAssignment(null);
    } catch {
      // Error handled
    }
  };

  const handleExtend = async () => {
    if (!extendAssignment || !extendEndDate || !extendReason) return;
    try {
      await extendMutation.mutateAsync({
        assignmentId: extendAssignment.id,
        new_end_date: extendEndDate,
        reason: extendReason,
      });
      setExtendAssignment(null);
    } catch {
      // Error handled
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Role Lifecycle Management"
        subtitle="Controlled role provisioning, singularity enforcement, and validity tracking (CFR-SA-005..009)"
        action={
          <Button leftSection={<FaPlus />} onClick={openAssign} color="violet">
            Assign Additional Role
          </Button>
        }
      />

      <Tabs defaultValue="assignments">
        <Tabs.List>
          <Tabs.Tab value="assignments" leftSection={<FaIdBadge size={14} />}>
            Active & Scheduled Assignments ({assignments.length})
          </Tabs.Tab>
          <Tabs.Tab value="definitions" leftSection={<FaHistory size={14} />}>
            Role Catalog ({roleDefs.length})
          </Tabs.Tab>
          <Tabs.Tab value="vacancies" leftSection={<FaTimes size={14} />}>
            Singular Vacancies ({vacancies.length})
          </Tabs.Tab>
        </Tabs.List>

        {/* Assignments Tab */}
        <Tabs.Panel value="assignments" pt="md">
          <Card withBorder p="md" radius="md">
            <Group justify="space-between" mb="md">
              <Select
                placeholder="Filter by Status"
                clearable
                data={[
                  { value: "active", label: "Active" },
                  { value: "scheduled", label: "Scheduled" },
                  { value: "expired", label: "Expired" },
                  { value: "revoked", label: "Revoked" },
                  { value: "reassigned", label: "Reassigned" },
                ]}
                value={filterStatus}
                onChange={setFilterStatus}
              />
            </Group>

            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>User ID</Table.Th>
                  <Table.Th>Role Name</Table.Th>
                  <Table.Th>Scope</Table.Th>
                  <Table.Th>Validity Window</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {assignments.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={6} style={{ textAlign: "center", padding: "40px 0" }}>
                      <Text c="dimmed">No role assignments recorded.</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  assignments.map((a) => (
                    <Table.Tr key={a.id}>
                      <Table.Td>
                        <Text fw={600} size="sm">
                          User #{a.user_id}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Text size="sm" fw={500}>
                            {a.role?.name || "Role"}
                          </Text>
                          {a.role?.is_singular && (
                            <Badge size="xs" color="violet" variant="outline">
                              Singular
                            </Badge>
                          )}
                        </Group>
                        <Text size="xs" c="dimmed">
                          {a.role?.code}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" tt="capitalize">
                          {a.scope_type}: {a.scope_id || "Global"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">
                          {a.start_date} → {a.end_date || "Indefinite"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <StatusBadge status={a.status} />
                      </Table.Td>
                      <Table.Td style={{ textAlign: "right" }}>
                        {a.status === "active" || a.status === "scheduled" ? (
                          <Group gap="xs" justify="flex-end">
                            <Tooltip label="Reassign Role">
                              <ActionIcon
                                variant="subtle"
                                color="teal"
                                onClick={() => {
                                  setReassignAssignment(a);
                                  setReassignNewUserId("");
                                  setReassignReason("");
                                }}
                              >
                                <FaExchangeAlt size={14} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label="Extend Validity">
                              <ActionIcon
                                variant="subtle"
                                color="blue"
                                onClick={() => {
                                  setExtendAssignment(a);
                                  setExtendEndDate("");
                                  setExtendReason("");
                                }}
                              >
                                <FaCalendarAlt size={14} />
                              </ActionIcon>
                            </Tooltip>
                            <Tooltip label="Revoke Role">
                              <ActionIcon
                                variant="subtle"
                                color="red"
                                onClick={() => {
                                  setRevokeAssignment(a);
                                  setRevokeReason("");
                                }}
                              >
                                <FaUserMinus size={14} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                        ) : null}
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        {/* Catalog Tab */}
        <Tabs.Panel value="definitions" pt="md">
          <Card withBorder p="md" radius="md">
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Role Name / Code</Table.Th>
                  <Table.Th>Module</Table.Th>
                  <Table.Th>Occupancy</Table.Th>
                  <Table.Th>Allowed Types</Table.Th>
                  <Table.Th>Conflicts</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {roleDefs.map((r) => (
                  <Table.Tr key={r.code}>
                    <Table.Td>
                      <Text fw={600} size="sm">
                        {r.name}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {r.code}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="dot" size="sm">
                        {r.module_association}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {r.is_singular ? (
                        <Badge color="violet" size="sm">
                          Singular (1 max)
                        </Badge>
                      ) : (
                        <Badge color="gray" size="sm">
                          Concurrent Allowed
                        </Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4}>
                        {r.allowed_user_types.map((t) => (
                          <Badge key={t} size="xs" variant="light">
                            {t}
                          </Badge>
                        ))}
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {r.conflict_role_codes.length > 0 ? r.conflict_role_codes.join(", ") : "None"}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        {/* Vacancies Tab */}
        <Tabs.Panel value="vacancies" pt="md">
          <Card withBorder p="md" radius="md">
            <Text size="sm" c="dimmed" mb="md">
              Singular institutional roles that currently have no active holder for the selected scope.
            </Text>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Role Name</Table.Th>
                  <Table.Th>Module</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {vacancies.length === 0 ? (
                  <Table.Tr>
                    <Table.Td colSpan={3} style={{ textAlign: "center", padding: "30px 0" }}>
                      <Text c="dimmed">All singular roles are currently occupied.</Text>
                    </Table.Td>
                  </Table.Tr>
                ) : (
                  vacancies.map((v) => (
                    <Table.Tr key={v.code}>
                      <Table.Td>
                        <Text fw={600} size="sm">
                          {v.name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {v.code}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge size="sm">{v.module_association}</Badge>
                      </Table.Td>
                      <Table.Td>
                        <Button
                          size="xs"
                          color="violet"
                          onClick={() => {
                            setAssignRoleCode(v.code);
                            openAssign();
                          }}
                        >
                          Fill Vacancy
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ))
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Assign Role Modal */}
      <Modal opened={assignOpened} onClose={closeAssign} title="Assign Additional Role" size="md">
        <Stack gap="sm">
          <NumberInput
            label="User ID"
            placeholder="Target internal User ID"
            required
            value={assignUserId}
            onChange={setAssignUserId}
          />

          <Select
            label="Role Definition"
            required
            data={roleDefs.map((r) => ({
              value: r.code,
              label: `${r.name} (${r.module_association})`,
            }))}
            value={assignRoleCode}
            onChange={(v) => setAssignRoleCode(v || "")}
          />

          <Group grow>
            <TextInput
              label="Start Date"
              type="date"
              required
              value={assignStartDate}
              onChange={(e) => setAssignStartDate(e.currentTarget.value)}
            />
            <TextInput
              label="End Date (Optional)"
              type="date"
              value={assignEndDate}
              onChange={(e) => setAssignEndDate(e.currentTarget.value)}
            />
          </Group>

          <Group grow>
            <Select
              label="Scope Type"
              data={["institute", "department", "hostel", "committee"]}
              value={assignScopeType}
              onChange={(v) => setAssignScopeType(v || "institute")}
            />
            <TextInput
              label="Scope ID"
              placeholder="e.g. CSE or Hall 3"
              value={assignScopeId}
              onChange={(e) => setAssignScopeId(e.currentTarget.value)}
            />
          </Group>

          <Textarea
            label="Reason / Order Reference"
            placeholder="e.g. Directorate order no. 124"
            required
            value={assignReason}
            onChange={(e) => setAssignReason(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={closeAssign}>
              Cancel
            </Button>
            <Button
              onClick={handleAssign}
              loading={assignMutation.isPending}
              disabled={!assignUserId || !assignRoleCode || !assignStartDate}
            >
              Assign Role
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reassign Modal */}
      <Modal
        opened={!!reassignAssignment}
        onClose={() => setReassignAssignment(null)}
        title="Reassign Role with Work Handover"
        size="md"
      >
        {reassignAssignment && (
          <Stack gap="sm">
            <Text size="sm">
              Reassigning <strong>{reassignAssignment.role?.name}</strong> from User #{reassignAssignment.user_id}.
            </Text>

            <NumberInput
              label="New Holder User ID"
              placeholder="User ID of successor"
              required
              value={reassignNewUserId}
              onChange={setReassignNewUserId}
            />

            <TextInput
              label="Handover Effective Date"
              type="date"
              required
              value={reassignEffectiveDate}
              onChange={(e) => setReassignEffectiveDate(e.currentTarget.value)}
            />

            <NumberInput
              label="Previous Holder Read-Only Audit Access (Days)"
              description="Retains read-only audit log visibility of their own tenure (BR-SA-013)"
              value={reassignAuditDays}
              onChange={setReassignAuditDays}
              min={0}
              max={365}
            />

            <Textarea
              label="Administrative Reason"
              required
              value={reassignReason}
              onChange={(e) => setReassignReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setReassignAssignment(null)}>
                Cancel
              </Button>
              <Button
                color="teal"
                onClick={handleReassign}
                loading={reassignMutation.isPending}
                disabled={!reassignNewUserId || !reassignReason}
              >
                Execute Handover
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Revoke Modal */}
      <Modal
        opened={!!revokeAssignment}
        onClose={() => setRevokeAssignment(null)}
        title="Revoke Role Assignment"
        size="md"
      >
        {revokeAssignment && (
          <Stack gap="sm">
            <Text size="sm">
              Revoking <strong>{revokeAssignment.role?.name}</strong> from User #{revokeAssignment.user_id}.
            </Text>

            <TextInput
              label="Effective Date"
              type="date"
              required
              value={revokeEffectiveDate}
              onChange={(e) => setRevokeEffectiveDate(e.currentTarget.value)}
              description={
                revokeEmergency
                  ? "Emergency revocation takes effect immediately"
                  : "Standard revocation requires at least 1 day notice (BR-SA-014)"
              }
            />

            <Checkbox
              label="Emergency Revocation (bypass notice period)"
              checked={revokeEmergency}
              onChange={(e) => {
                setRevokeEmergency(e.currentTarget.checked);
                if (e.currentTarget.checked) {
                  setRevokeEffectiveDate(new Date().toISOString().split("T")[0]);
                }
              }}
            />

            <Select
              label="Pending Task Disposition"
              data={[
                { value: "transfer", label: "Transfer to department / superior" },
                { value: "close", label: "Close pending requests" },
              ]}
              value={revokeDisposition}
              onChange={(v) => setRevokeDisposition((v as "transfer" | "close") || "transfer")}
            />

            <Textarea
              label="Revocation Reason"
              required
              value={revokeReason}
              onChange={(e) => setRevokeReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRevokeAssignment(null)}>
                Cancel
              </Button>
              <Button
                color="red"
                onClick={handleRevoke}
                loading={revokeMutation.isPending}
                disabled={!revokeReason}
              >
                Confirm Revocation
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Extend Modal */}
      <Modal
        opened={!!extendAssignment}
        onClose={() => setExtendAssignment(null)}
        title="Extend Role Validity Period"
        size="md"
      >
        {extendAssignment && (
          <Stack gap="sm">
            <Text size="sm">
              Current validity: {extendAssignment.start_date} → {extendAssignment.end_date || "Indefinite"}
            </Text>

            <TextInput
              label="New End Date"
              type="date"
              required
              value={extendEndDate}
              onChange={(e) => setExtendEndDate(e.currentTarget.value)}
              description="Must be strictly after the current end date (BR-SA-016)"
            />

            <Textarea
              label="Extension Rationale"
              required
              value={extendReason}
              onChange={(e) => setExtendReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setExtendAssignment(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleExtend}
                loading={extendMutation.isPending}
                disabled={!extendEndDate || !extendReason}
              >
                Save Extension
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
