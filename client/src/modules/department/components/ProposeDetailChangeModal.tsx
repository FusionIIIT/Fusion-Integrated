import { useState } from "react";
import { Select, Stack, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useProposeDetailChange } from "../api/hooks";

interface Props {
  opened: boolean;
  onClose: () => void;
  departmentId: number;
}

export function ProposeDetailChangeModal({ opened, onClose, departmentId }: Props) {
  const [fieldName, setFieldName] = useState("core_policies");
  const [proposedValue, setProposedValue] = useState("");

  const propose = useProposeDetailChange();

  const handleSubmit = async () => {
    if (!proposedValue.trim()) return;
    try {
      await propose.mutateAsync({
        department: departmentId,
        field_name: fieldName,
        proposed_value: proposedValue.trim(),
      });
      notifications.show({
        title: "Proposal Submitted",
        message: "Your proposed change has been submitted for administrative review.",
        color: "teal",
      });
      setProposedValue("");
      onClose();
    } catch (e) {
      notifications.show({
        title: "Proposal Failed",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Propose Detail Change"
      subtitle="Submit an update proposal for official department information"
      onSubmit={handleSubmit}
      submitting={propose.isPending}
      disabled={!proposedValue.trim()}
    >
      <Stack gap="sm">
        <Select
          label="Field to Modify"
          data={[
            { value: "core_policies", label: "Core Policies & Guidelines" },
            { value: "name", label: "Department Display Name" },
          ]}
          value={fieldName}
          onChange={(v) => setFieldName(v || "core_policies")}
          required
        />
        <Textarea
          label="Proposed Value"
          placeholder="Enter new proposed content..."
          required
          minRows={5}
          value={proposedValue}
          onChange={(e) => setProposedValue(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
