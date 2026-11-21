import { useState } from "react";
import { Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { errorMessage } from "../../../lib/http";
import { useSubmitFeedback } from "../api/hooks";

interface Props {
  opened: boolean;
  onClose: () => void;
  departmentId: number;
}

export function SubmitFeedbackModal({ opened, onClose, departmentId }: Props) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState("academic");

  const submitFb = useSubmitFeedback();

  const handleSubmit = async () => {
    if (!subject.trim() || !body.trim()) return;
    try {
      await submitFb.mutateAsync({
        department: departmentId,
        subject: subject.trim(),
        body: body.trim(),
        category,
      });
      notifications.show({
        title: "Feedback Submitted",
        message: "Your submission has been securely delivered to department staff.",
        color: "teal",
      });
      setSubject("");
      setBody("");
      onClose();
    } catch (e) {
      notifications.show({
        title: "Failed to Submit Feedback",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Submit Feedback / Grievance"
      subtitle="Confidential submission to department administrators"
      onSubmit={handleSubmit}
      submitting={submitFb.isPending}
      disabled={!subject.trim() || !body.trim()}
    >
      <Stack gap="sm">
        <TextInput
          label="Subject"
          placeholder="Brief summary of feedback..."
          required
          value={subject}
          onChange={(e) => setSubject(e.currentTarget.value)}
        />
        <Select
          label="Category"
          data={[
            { value: "academic", label: "Academic / Coursework" },
            { value: "laboratory", label: "Laboratory / Equipment" },
            { value: "administrative", label: "Administrative / Policy" },
            { value: "infrastructure", label: "Classroom / Infrastructure" },
            { value: "other", label: "Other" },
          ]}
          value={category}
          onChange={(v) => setCategory(v || "academic")}
        />
        <Textarea
          label="Description"
          placeholder="Provide specific details..."
          required
          minRows={4}
          value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
