import { useState } from "react";
import {
  Alert,
  NumberInput,
  Stack,
  Switch,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExchangeAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { FormRow, FormSection } from "../../../ui/components/FormSection";
import { useReassignRole } from "../api/hooks";
import type { RoleAssignment } from "../api/types";

export function RoleHandoverModal({
  assignment,
  opened,
  onClose,
}: {
  assignment: RoleAssignment | null;
  opened: boolean;
  onClose: () => void;
}) {
  const reassignRole = useReassignRole();

  const [newHolderId, setNewHolderId] = useState<number | string>("");
  const [effectiveDate, setEffectiveDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [handoverTasks, setHandoverTasks] = useState(true);
  const [auditDays, setAuditDays] = useState<number | string>(90);
  const [reason, setReason] = useState("");

  if (!assignment) return null;

  const handleSubmit = () => {
    if (!newHolderId || !reason.trim() || !effectiveDate) {
      notifications.show({
        color: "red",
        title: "Required Fields Missing",
        message: "New Holder User ID, Effective Date, and Reason are required.",
      });
      return;
    }

    reassignRole.mutate(
      {
        current_assignment_id: assignment.id,
        new_holder_id: Number(newHolderId),
        effective_date: effectiveDate,
        handover_tasks: handoverTasks,
        audit_access_days: Number(auditDays) || 90,
        reason: reason.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Role Handed Over",
            message: `Role ${assignment.role_id} successfully transferred to user #${newHolderId}.`,
          });
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Handover Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Atomic Role Handover"
      subtitle={`Transfer '${assignment.role_id}' from current user #${assignment.user_id}`}
      onSubmit={handleSubmit}
      submitting={reassignRole.isPending}
      submitLabel="Execute Handover"
      size="md"
    >
      <Stack gap="md">
        <Alert icon={<FaExchangeAlt size={16} />} color="blue">
          Role Handover automatically expires the current holder's assignment and
          instantiates a new assignment for the incoming holder in a single atomic
          transaction (UC-SA-007).
        </Alert>

        <FormSection title="Incoming Holder">
          <FormRow>
            <NumberInput
              label="New Holder User ID"
              placeholder="e.g. 108"
              value={newHolderId}
              onChange={setNewHolderId}
              required
              min={1}
            />
            <TextInput
              label="Effective Date"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.currentTarget.value)}
              required
            />
          </FormRow>
        </FormSection>

        <FormSection title="Transition Parameters">
          <FormRow>
            <Switch
              label="Handover Pending Tasks"
              description="Reassign unresolved workflow tasks to new holder"
              checked={handoverTasks}
              onChange={(e) => setHandoverTasks(e.currentTarget.checked)}
              mt="xs"
            />
            <NumberInput
              label="Read-Only Audit Window (Days)"
              description="Outgoing holder retention for historical queries"
              value={auditDays}
              onChange={setAuditDays}
              min={0}
              max={365}
            />
          </FormRow>

          <Textarea
            label="Handover Audit Justification"
            placeholder="Official handover reason (e.g. tenure completion, committee rotation)..."
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            required
            rows={2}
          />
        </FormSection>
      </Stack>
    </FormModal>
  );
}
