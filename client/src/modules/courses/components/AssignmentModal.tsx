import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Modal,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";

import { createAssignment, updateAssignment } from "../api/hooks";
import type { CourseAssignment } from "../api/types";

interface AssignmentModalProps {
  opened: boolean;
  onClose: () => void;
  workspaceId: number;
  assignment?: CourseAssignment | null;
  onSuccess: () => void;
}

export function AssignmentModal({
  opened,
  onClose,
  workspaceId,
  assignment,
  onSuccess,
}: AssignmentModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dueDate, setDueDate] = useState<Date | null>(null);
  const [isPublished, setIsPublished] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (assignment) {
      setTitle(assignment.title);
      setDescription(assignment.description || "");
      setInstructions(assignment.instructions || "");
      setDueDate(assignment.due_at ? new Date(assignment.due_at) : null);
      setIsPublished(assignment.is_published);
    } else {
      setTitle("");
      setDescription("");
      setInstructions("");
      setDueDate(null);
      setIsPublished(false); // Default to draft per BR-LMS-010
    }
    setError(null);
  }, [assignment, opened]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please provide an assignment title.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (assignment) {
        await updateAssignment(workspaceId, assignment.id, {
          title: title.trim(),
          description: description.trim(),
          instructions: instructions.trim(),
          due_at: dueDate ? dueDate.toISOString() : null,
          clear_due_at: !dueDate,
          is_published: isPublished,
        });
      } else {
        await createAssignment(workspaceId, {
          title: title.trim(),
          description: description.trim(),
          instructions: instructions.trim(),
          due_at: dueDate ? dueDate.toISOString() : null,
          is_published: isPublished,
        });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to save assignment. Please check your inputs.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={assignment ? "Edit Assignment" : "Create Course Assignment"}
      size="lg"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {error && (
            <Alert color="red" title="Error">
              {error}
            </Alert>
          )}

          <TextInput
            label="Assignment Title"
            placeholder="e.g. Lab Assignment 1: Self-Balancing Trees"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
            maxLength={200}
          />

          <Textarea
            label="Description / Objective"
            placeholder="High-level description of this assignment and objectives..."
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            minRows={3}
            autosize
          />

          <Textarea
            label="Instructions & Guidelines"
            placeholder="Detailed task instructions, problem statements, or submission guidelines..."
            value={instructions}
            onChange={(e) => setInstructions(e.currentTarget.value)}
            minRows={5}
            autosize
          />

          <DateTimePicker
            label="Submission Deadline (Optional)"
            placeholder="Pick deadline date and time"
            value={dueDate}
            onChange={setDueDate}
            clearable
            description="Optional deadline for this assignment. If set, students will see the deadline and whether it has passed."
          />

          <Checkbox
            label="Publish assignment"
            description="If unchecked, this assignment remains in Draft state visible only to faculty instructors (BR-LMS-010)."
            checked={isPublished}
            onChange={(e) => setIsPublished(e.currentTarget.checked)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              {assignment ? "Save Changes" : "Create Assignment"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

