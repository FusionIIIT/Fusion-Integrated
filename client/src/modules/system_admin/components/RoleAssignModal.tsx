import { useState } from "react";
import {
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { FormRow, FormSection } from "../../../ui/components/FormSection";
import { useAssignRole } from "../api/hooks";
import type { RoleDefinition } from "../api/types";

export function RoleAssignModal({
  opened,
  onClose,
  definitions,
}: {
  opened: boolean;
  onClose: () => void;
  definitions: RoleDefinition[];
}) {
  const assignRole = useAssignRole();

  const [roleCode, setRoleCode] = useState<string | null>(null);
  const [userId, setUserId] = useState<number | string>("");
  const [scope, setScope] = useState("");
  const [startDate, setStartDate] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  const resetForm = () => {
    setRoleCode(null);
    setUserId("");
    setScope("");
    setStartDate(new Date().toISOString().split("T")[0]);
    setEndDate("");
    setReason("");
  };

  const roleOptions = definitions.map((d) => ({
    value: d.code,
    label: `${d.label} (${d.code})`,
  }));

  const handleSubmit = () => {
    if (!roleCode || !userId || !reason.trim() || !startDate) {
      notifications.show({
        color: "red",
        title: "Required Fields Missing",
        message: "Role, User ID, Start Date, and Audit Reason are required.",
      });
      return;
    }

    assignRole.mutate(
      {
        user_id: Number(userId),
        role_code: roleCode,
        scope: scope.trim() || undefined,
        start_date: startDate,
        end_date: endDate || null,
        reason: reason.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Role Assigned",
            message: `Role ${roleCode} assigned to user #${userId}.`,
          });
          resetForm();
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Assignment Failed",
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
      title="Assign Institutional Role"
      subtitle="Delegate administrative authority or functional role to a user"
      onSubmit={handleSubmit}
      submitting={assignRole.isPending}
      submitLabel="Assign Role"
      size="md"
    >
      <Stack gap="md">
        <FormSection title="Role & Recipient">
          <Select
            label="Role Definition"
            placeholder="Select authority role"
            data={roleOptions}
            value={roleCode}
            onChange={setRoleCode}
            required
            searchable
          />

          <FormRow>
            <NumberInput
              label="User ID"
              placeholder="e.g. 104"
              value={userId}
              onChange={setUserId}
              required
              min={1}
            />
            <TextInput
              label="Scope / Department"
              placeholder="e.g. CSE / Hostel 3"
              value={scope}
              onChange={(e) => setScope(e.currentTarget.value)}
            />
          </FormRow>
        </FormSection>

        <FormSection title="Validity & Authorization">
          <FormRow>
            <TextInput
              label="Start Date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
              required
            />
            <TextInput
              label="End Date (Optional)"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />
          </FormRow>

          <Textarea
            label="Audit Reason"
            placeholder="Official justification for role delegation (required)..."
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
