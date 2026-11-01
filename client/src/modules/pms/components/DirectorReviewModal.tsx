import { useState } from "react";
import { Alert, Select, Stack, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useSubmitDirectorReview } from "../api/hooks";

export function DirectorReviewModal({
  applicationId,
  opened,
  onClose,
}: {
  applicationId: number | null;
  opened: boolean;
  onClose: () => void;
}) {
  const [decision, setDecision] = useState<string>("approved");
  const [justification, setJustification] = useState<string>("");
  const reviewMutation = useSubmitDirectorReview(applicationId ?? 0);

  const handleSubmit = async () => {
    if (!applicationId) return;

    if (!justification.trim()) {
      notifications.show({
        color: "red",
        message: "Mandatory review justification is required (BR-PMS-011).",
      });
      return;
    }

    try {
      await reviewMutation.mutateAsync({
        decision,
        justification: justification.trim(),
      });
      notifications.show({
        color: "green",
        message: `Application decision '${decision}' successfully recorded.`,
      });
      setJustification("");
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
      title="Director Application Review"
      onSubmit={handleSubmit}
      submitLabel="Record Decision"
      submitting={reviewMutation.isPending}
      danger={decision === "rejected"}
    >
      <Stack gap="md">
        <Select
          label="Decision"
          description="Director determination (BR-PMS-011..013)"
          value={decision}
          onChange={(val) => setDecision(val ?? "approved")}
          data={[
            { value: "approved", label: "Approve for Patent Prosecution" },
            { value: "revisions_requested", label: "Request Revisions from Applicant" },
            { value: "rejected", label: "Reject Application" },
          ]}
          required
        />

        <Textarea
          label="Justification & Feedback"
          description="Detailed review grounds and instructions for inventors / PCC."
          placeholder="State substantive feedback, novelty evaluation, or revision requirements..."
          minRows={4}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          required
        />

        {decision === "rejected" && (
          <Alert color="red" variant="light">
            Rejecting will close internal prosecution. Applicant retains right of appeal.
          </Alert>
        )}
      </Stack>
    </FormModal>
  );
}
