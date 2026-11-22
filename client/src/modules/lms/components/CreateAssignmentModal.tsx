import React, { useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { getApiErrorMessage, useCreateAssignment } from "../api/hooks";
import type { ModuleSection, SubmissionType } from "../api/types";

export interface CreateAssignmentModalProps {
  opened: boolean;
  onClose: () => void;
  courseId: number;
  sections: ModuleSection[];
}

export const CreateAssignmentModal: React.FC<CreateAssignmentModalProps> = ({
  opened,
  onClose,
  courseId,
  sections,
}) => {
  const [title, setTitle] = useState("");
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [pointsPossible, setPointsPossible] = useState<number | string>(100);
  const [dueDate, setDueDate] = useState("");
  const [submissionType, setSubmissionType] = useState<SubmissionType>("file");
  const [isPublished, setIsPublished] = useState(true);
  const [scheduledPublishAt, setScheduledPublishAt] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const createAssignmentMutation = useCreateAssignment();

  const handleClose = () => {
    setErrorMsg(null);
    setTitle("");
    setSectionId(null);
    setDescription("");
    setPointsPossible(100);
    setDueDate("");
    setSubmissionType("file");
    setIsPublished(true);
    setScheduledPublishAt("");
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      if (!dueDate) {
        setErrorMsg("Due date is required.");
        setIsSubmitting(false);
        return;
      }

      const numPoints = typeof pointsPossible === "number" ? pointsPossible : parseInt(pointsPossible) || 100;
      await createAssignmentMutation.mutateAsync({
        course: courseId,
        section: sectionId ? parseInt(sectionId) : null,
        title,
        description: description || undefined,
        points_possible: numPoints,
        due_date: new Date(dueDate).toISOString(),
        submission_type: submissionType,
        is_published: isPublished,
        scheduled_publish_at: scheduledPublishAt ? new Date(scheduledPublishAt).toISOString() : undefined,
      });

      handleClose();
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const sectionOptions = sections.map((s) => ({
    value: String(s.id),
    label: s.title,
  }));

  return (
    <Modal opened={opened} onClose={handleClose} title="Create New Course Assignment" size="lg">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert color="red" title="Error" withCloseButton onClose={() => setErrorMsg(null)}>
              {errorMsg}
            </Alert>
          )}

          <TextInput
            label="Assignment Title"
            placeholder="e.g. Problem Set 1: Graph Algorithms"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
          />

          <Select
            label="Module / Section"
            placeholder="Select module section (optional)"
            data={sectionOptions}
            value={sectionId}
            onChange={setSectionId}
            clearable
          />

          <Textarea
            label="Instructions & Description"
            placeholder="Detailed instructions for students..."
            minRows={4}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />

          <Group grow>
            <NumberInput
              label="Maximum Points"
              value={pointsPossible}
              onChange={(val) => setPointsPossible(val)}
              min={1}
              required
            />

            <Select
              label="Submission Mode"
              data={[
                { label: "File Upload", value: "file" },
                { label: "Text Response", value: "text" },
                { label: "Website Link", value: "link" },
              ]}
              value={submissionType}
              onChange={(val) => setSubmissionType((val as SubmissionType) || "file")}
              required
            />
          </Group>

          <TextInput
            label="Due Date and Time"
            type="datetime-local"
            value={dueDate}
            onChange={(e) => setDueDate(e.currentTarget.value)}
            required
          />

          <Checkbox
            label="Publish Immediately"
            checked={isPublished}
            onChange={(e) => setIsPublished(e.currentTarget.checked)}
          />

          <TextInput
            label="Scheduled Release Date & Time (Optional)"
            type="datetime-local"
            value={scheduledPublishAt}
            onChange={(e) => setScheduledPublishAt(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              Create Assignment
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default CreateAssignmentModal;
