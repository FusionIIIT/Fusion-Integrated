import { useState } from "react";
import { Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useRecordOfficeAction } from "../api/hooks";

export function OfficeActionModal({
  applicationId,
  opened,
  onClose,
}: {
  applicationId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [actionNumber, setActionNumber] = useState<string>("FER-01");
  const [actionType, setActionType] = useState<string>("FER");
  const [issueDate, setIssueDate] = useState<string>(
    new Date().toISOString().split("T")[0] || ""
  );
  const [deadline, setDeadline] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  const oaMutation = useRecordOfficeAction(applicationId ?? 0);

  const handleSubmit = async () => {
    if (!applicationId || !actionNumber.trim() || !deadline) return;

    try {
      await oaMutation.mutateAsync({
        action_number: actionNumber.trim(),
        action_type: actionType,
        issue_date: issueDate,
        response_deadline: deadline,
        description: description.trim(),
      });
      notifications.show({
        color: "green",
        message: "Office Action logged successfully (BR-PMS-041).",
      });
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Log Patent Office Examination Report"
      onSubmit={handleSubmit}
      submitLabel="Log Office Action"
      submitting={oaMutation.isPending}
      disabled={!deadline || !actionNumber.trim()}
      disabledReason={!deadline ? "Statutory deadline is required" : undefined}
    >
      <Stack gap="md">
        <Select
          label="Examination Report / Office Action Type"
          value={actionType}
          onChange={(val) => setActionType(val ?? "FER")}
          data={[
            { value: "FER", label: "First Examination Report (FER)" },
            { value: "SER", label: "Second Examination Report (SER)" },
            { value: "HEARING", label: "Hearing Notice under Sec 14/15" },
            { value: "NON_FINAL_REJECTION", label: "Non-Final Rejection (USPTO)" },
            { value: "FINAL_REJECTION", label: "Final Rejection (USPTO)" },
          ]}
          required
        />

        <TextInput
          label="Official Reference / Action Number"
          placeholder="E.g. IPO/DEL/FER/2026/8912"
          value={actionNumber}
          onChange={(e) => setActionNumber(e.target.value)}
          required
        />

        <TextInput
          label="Issue Date"
          type="date"
          value={issueDate}
          onChange={(e) => setIssueDate(e.target.value)}
          required
        />

        <TextInput
          label="Statutory Response Deadline (6 months standard)"
          type="date"
          value={deadline}
          onChange={(e) => setDeadline(e.target.value)}
          required
        />

        <Textarea
          label="Examiner Objections & Prior Art Citations"
          placeholder="Summary of Section 2(1)(j), Section 3 objections, cited D1/D2 prior art..."
          minRows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
      </Stack>
    </FormModal>
  );
}
