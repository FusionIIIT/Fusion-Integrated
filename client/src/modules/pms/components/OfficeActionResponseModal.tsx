import { useState } from "react";
import { Checkbox, Stack, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useDraftOfficeActionResponse } from "../api/hooks";

export function OfficeActionResponseModal({
  actionId,
  opened,
  onClose,
}: {
  actionId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [draftText, setDraftText] = useState<string>("Draft arguments distinguishing prior art.");
  const [requireApplicantApproval, setRequireApplicantApproval] = useState<boolean>(true);

  const draftMutation = useDraftOfficeActionResponse(actionId ?? 0);

  const handleSubmit = async () => {
    if (!actionId || !draftText.trim()) return;

    try {
      await draftMutation.mutateAsync({
        draft_text: draftText.trim(),
        requires_applicant_approval: requireApplicantApproval,
      });
      notifications.show({
        color: "green",
        message: "Office action response drafted (BR-PMS-042).",
      });
      setDraftText("");
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
      title="Draft Office Action Response"
      onSubmit={handleSubmit}
      submitLabel="Save Response Draft"
      submitting={draftMutation.isPending}
      disabled={!draftText.trim()}
      disabledReason={!draftText.trim() ? "Draft text is required" : undefined}
    >
      <Stack gap="md">
        <Textarea
          label="Response Arguments & Claim Amendments"
          placeholder="Point-by-point rebuttal to examiner objections, claim scope amendments, distinguishing cited art..."
          minRows={6}
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          required
        />

        <Checkbox
          label="Require lead applicant / inventor sign-off before official submission (BR-PMS-043)"
          checked={requireApplicantApproval}
          onChange={(e) => setRequireApplicantApproval(e.currentTarget.checked)}
        />
      </Stack>
    </FormModal>
  );
}
