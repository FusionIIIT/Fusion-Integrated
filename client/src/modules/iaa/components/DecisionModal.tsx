import { useState } from "react";
import { Modal, Button, Textarea, Group, Text } from "@mantine/core";

interface DecisionModalProps {
  opened: boolean;
  onClose: () => void;
  decision: "approve" | "reject";
  targetTitle: string;
  onConfirm: (remarks: string) => Promise<void>;
}

export function DecisionModal({ opened, onClose, decision, targetTitle, onConfirm }: DecisionModalProps) {
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!remarks.trim()) {
      setError("Decision remarks are mandatory (IAA-BR-005).");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onConfirm(remarks);
      setRemarks("");
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to record decision.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={<Text fw={600}>{decision === "approve" ? "Approve Request" : "Reject Request"}</Text>}
      centered
    >
      <Text size="sm" mb="sm">
        Confirm recording {decision} decision for: <strong>{targetTitle}</strong>
      </Text>
      <Textarea
        label="Decision Remarks (Mandatory)"
        placeholder="Enter required remarks..."
        minRows={3}
        value={remarks}
        onChange={(e) => setRemarks(e.currentTarget.value)}
        error={error}
        required
        mb="md"
      />
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          color={decision === "approve" ? "green" : "red"}
          onClick={handleConfirm}
          loading={submitting}
        >
          Confirm {decision === "approve" ? "Approval" : "Rejection"}
        </Button>
      </Group>
    </Modal>
  );
}
