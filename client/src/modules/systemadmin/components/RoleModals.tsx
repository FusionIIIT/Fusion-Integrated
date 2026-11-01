import { useState } from "react";
import {
  Modal,
  TextInput,
  Select,
  Stack,
  Button,
  Group,
  Textarea,
  Text,
  Alert,
  Checkbox,
} from "@mantine/core";
import { useAssignRole, useReassignRole, useRevokeRole, useExtendRole } from "../api/hooks";
import type { RoleDefinitionItem, RoleAssignmentItem } from "../api/types";
import { errorMessage } from "../../../lib/http";

export function AssignRoleModal({
  roles,
  opened,
  onClose,
}: {
  roles: RoleDefinitionItem[];
  opened: boolean;
  onClose: () => void;
}) {
  const [roleCode, setRoleCode] = useState<string>(roles[0]?.code ?? "");
  const [userId, setUserId] = useState<string>("");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState("");
  const [scope, setScope] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const assignMutation = useAssignRole();

  const selectedRole = roles.find((r) => r.code === roleCode);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await assignMutation.mutateAsync({
        role_code: roleCode,
        user_id: Number(userId),
        start_date: startDate,
        end_date: endDate || null,
        scope,
        reason,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Assign Additional Role" size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Select
            label="Role Definition"
            data={roles.map((r) => ({
              value: r.code,
              label: `${r.name} (${r.code}) ${r.is_singular ? "• Singular" : ""}`,
            }))}
            value={roleCode}
            onChange={(val) => setRoleCode(val ?? "")}
            required
          />
          {selectedRole && (
            <Text size="xs" c="dimmed">
              Allowed User Types: {selectedRole.allowed_user_types.join(", ")} | Time-Bound:{" "}
              {selectedRole.is_time_bound ? "Yes" : "No"}
            </Text>
          )}
          <TextInput
            label="Target User ID (Internal ID)"
            placeholder="e.g. 1"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
          />
          <Group grow>
            <TextInput
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
            <TextInput
              label="End Date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required={selectedRole?.is_time_bound}
            />
          </Group>
          <TextInput
            label="Scope (Optional)"
            placeholder="e.g. CSE Department or Hall 4"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          />
          <Textarea
            label="Assignment Justification"
            placeholder="Reason for appointment..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={assignMutation.isPending}>Assign Role</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function ReassignRoleModal({
  assignment,
  opened,
  onClose,
}: {
  assignment: RoleAssignmentItem;
  opened: boolean;
  onClose: () => void;
}) {
  const [newUserId, setNewUserId] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(
    new Date(Date.now() + 86400000 * 2).toISOString().slice(0, 10)
  );
  const [disposition, setDisposition] = useState<"transfer" | "close">("transfer");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reassignMutation = useReassignRole(assignment.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await reassignMutation.mutateAsync({
        new_user_id: Number(newUserId),
        effective_date: effectiveDate,
        pending_task_disposition: disposition,
        reason,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`Reassign Role: ${assignment.role_details.name}`}
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Current Holder: <b>{assignment.user_details.full_name}</b> ({assignment.user_details.institute_id})
          </Text>
          <Text size="xs" c="dimmed">
            Previous holder will retain 30-day read-only audit access for handover continuity (BR-SA-013).
          </Text>
          <TextInput
            label="New Holder User ID"
            placeholder="Internal user ID"
            value={newUserId}
            onChange={(e) => setNewUserId(e.target.value)}
            required
          />
          <TextInput
            label="Effective Handover Date"
            type="date"
            value={effectiveDate}
            onChange={(e) => setEffectiveDate(e.target.value)}
            required
          />
          <Select
            label="Pending Tasks Disposition"
            data={[
              { value: "transfer", label: "Transfer active workflows to new holder" },
              { value: "close", label: "Close pending actions" },
            ]}
            value={disposition}
            onChange={(val) => setDisposition((val as "transfer" | "close") ?? "transfer")}
            required
          />
          <Textarea
            label="Handover & Reassignment Notes"
            placeholder="Details of appointment and transition..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={reassignMutation.isPending}>Reassign Role</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function RevokeRoleModal({
  assignment,
  opened,
  onClose,
}: {
  assignment: RoleAssignmentItem;
  opened: boolean;
  onClose: () => void;
}) {
  const [isEmergency, setIsEmergency] = useState(false);
  const [effectiveDate, setEffectiveDate] = useState(
    new Date(Date.now() + 86400000 * 2).toISOString().slice(0, 10)
  );
  const [disposition, setDisposition] = useState<"transfer" | "close">("close");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const revokeMutation = useRevokeRole(assignment.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await revokeMutation.mutateAsync({
        is_emergency: isEmergency,
        effective_date: isEmergency ? null : effectiveDate,
        pending_task_disposition: disposition,
        reason,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`Revoke Role Assignment: ${assignment.role_details.name}`}
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Revoking role for: <b>{assignment.user_details.full_name}</b> ({assignment.user_details.institute_id})
          </Text>
          <Checkbox
            label="Emergency Immediate Revocation (no advance notice)"
            checked={isEmergency}
            onChange={(e) => setIsEmergency(e.currentTarget.checked)}
          />
          {!isEmergency && (
            <TextInput
              label="Effective Date (requires at least 1 day notice)"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              required
            />
          )}
          <Select
            label="Pending Workflow Tasks Disposition"
            data={[
              { value: "close", label: "Close and cancel pending requests" },
              { value: "transfer", label: "Transfer to supervisor" },
            ]}
            value={disposition}
            onChange={(val) => setDisposition((val as "transfer" | "close") ?? "close")}
            required
          />
          <Textarea
            label="Revocation Justification (Mandatory)"
            placeholder="State reason for role revocation..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" color="red" loading={revokeMutation.isPending}>Revoke Role</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function ExtendRoleModal({
  assignment,
  opened,
  onClose,
}: {
  assignment: RoleAssignmentItem;
  opened: boolean;
  onClose: () => void;
}) {
  const [newEndDate, setNewEndDate] = useState(
    new Date(Date.now() + 86400000 * 180).toISOString().slice(0, 10)
  );
  const [approvalRef, setApprovalRef] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const extendMutation = useExtendRole(assignment.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await extendMutation.mutateAsync({
        new_end_date: newEndDate,
        extension_approval_ref: approvalRef,
        reason,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`Extend Role Validity: ${assignment.role_details.name}`}
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Current Tenure End Date: <b>{assignment.end_date || "None"}</b>
          </Text>
          <TextInput
            label="New End Date"
            type="date"
            value={newEndDate}
            onChange={(e) => setNewEndDate(e.target.value)}
            required
          />
          <TextInput
            label="Extension Approval Authority Reference"
            placeholder="e.g. DIR/EXT/2026/04"
            value={approvalRef}
            onChange={(e) => setApprovalRef(e.target.value)}
            required
          />
          <Textarea
            label="Extension Reason"
            placeholder="Official justification..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={extendMutation.isPending}>Extend Validity</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
