import { useState } from "react";
import { Button, Group, Modal, Select, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useReviewDecision } from "../api/hooks";

export function ReviewDecisionModal({
  opened,
  onClose,
  applicationId,
  applicationTitle,
}: {
  opened: boolean;
  onClose: () => void;
  applicationId: number;
  applicationTitle: string;
}) {
  const [decision, setDecision] = useState<"APPROVE" | "REJECT" | "REQUEST_REVISIONS">("APPROVE");
  const [justification, setJustification] = useState("");
  const review = useReviewDecision(applicationId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (justification.trim().length < 50) {
      notifications.show({
        color: "red",
        title: "Justification too short",
        message: "Technical review justification must be at least 50 characters (BR-PMS-031).",
      });
      return;
    }
    review.mutate(
      { decision, justification },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Review submitted",
            message: `Application marked as ${decision}.`,
          });
          setJustification("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Review failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Record Director Review Decision">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm">
            Reviewing <strong>{applicationTitle}</strong>
          </Text>
          <Select
            label="Decision"
            data={[
              { value: "APPROVE", label: "Approve (Recommend for Patenting)" },
              { value: "REQUEST_REVISIONS", label: "Request Revisions" },
              { value: "REJECT", label: "Reject Application" },
            ]}
            value={decision}
            onChange={(val) => setDecision((val as "APPROVE" | "REJECT" | "REQUEST_REVISIONS") ?? "APPROVE")}
            required
          />
          <Textarea
            label="Technical Justification"
            description="Minimum 50 characters required by BR-PMS-031"
            placeholder="Detailed technical rationale for this decision..."
            required
            minRows={4}
            value={justification}
            onChange={(e) => setJustification(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={review.isPending}>
              Cancel
            </Button>
            <Button
              color={decision === "REJECT" ? "red" : decision === "APPROVE" ? "teal" : "orange"}
              type="submit"
              loading={review.isPending}
            >
              Submit Decision
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
