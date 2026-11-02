import React, { useState } from "react";
import {
  Alert,
  Anchor,
  Button,
  Group,
  Modal,
  NumberInput,
  Paper,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { getApiErrorMessage, getFileDownloadUrl, useGradeSubmission } from "../api/hooks";
import type { Assignment, Role, Submission } from "../api/types";

export interface GradingModalProps {
  opened: boolean;
  onClose: () => void;
  submission: Submission;
  assignment: Assignment;
  userRole?: Role;
}

export const GradingModal: React.FC<GradingModalProps> = ({
  opened,
  onClose,
  submission,
  assignment,
  userRole = "instructor",
}) => {
  const [points, setPoints] = useState<number | string>(0);
  const [feedback, setFeedback] = useState("");
  const [reason, setReason] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isTa = userRole === "ta";
  const gradeMutation = useGradeSubmission(submission.id);

  const handleClose = () => {
    setErrorMsg(null);
    setPoints(0);
    setFeedback("");
    setReason("");
    onClose();
  };

  const handleGrade = async (action: "draft" | "release") => {
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const numPoints = typeof points === "number" ? points : parseFloat(points) || 0;
      await gradeMutation.mutateAsync({
        action,
        points: numPoints,
        feedback,
        reason: action === "release" ? reason || "initial grade release" : undefined,
        role: userRole,
      });
      handleClose();
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal opened={opened} onClose={handleClose} title="Assess Student Submission" size="lg">
      <Stack gap="md">
        {errorMsg && (
          <Alert color="red" title="Grading Policy Notice" withCloseButton onClose={() => setErrorMsg(null)}>
            {errorMsg}
          </Alert>
        )}

        {isTa && (
          <Alert color="blue" title="TA Authorization Policy (BW-LMS-05 / ISS-LMS-002)">
            As a Teaching Assistant, your assessments are recorded in Draft mode. Official grade release to students is reserved for Course Instructors.
          </Alert>
        )}

        <Paper withBorder p="sm" radius="md">
          <Text size="xs" c="dimmed" mb={4}>
            Submission by Student #{submission.student_user_id} • Version {submission.version} • {new Date(submission.submitted_at).toLocaleString()}
          </Text>

          {submission.submission_type === "text" && submission.content_text && (
            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
              {submission.content_text}
            </Text>
          )}

          {submission.submission_type === "link" && submission.link_url && (
            <Anchor href={submission.link_url} target="_blank" rel="noopener noreferrer" size="sm">
              {submission.link_url} ↗
            </Anchor>
          )}

          {submission.submission_type === "file" && submission.file_storage_key && (
            <Button
              component="a"
              href={getFileDownloadUrl(submission.file_storage_key)}
              download
              variant="light"
              size="xs"
            >
              Download Submitted File
            </Button>
          )}
        </Paper>

        <NumberInput
          label={`Points Awarded (Max: ${assignment.points_possible})`}
          placeholder="0"
          min={0}
          max={assignment.points_possible}
          value={points}
          onChange={(val) => setPoints(val)}
          required
        />

        <Textarea
          label="Feedback for Student"
          placeholder="Constructive evaluation notes..."
          minRows={3}
          value={feedback}
          onChange={(e) => setFeedback(e.currentTarget.value)}
        />

        {!isTa && (
          <TextInput
            label="Release Reason / Audit Note"
            placeholder="e.g. initial rubric grading completed"
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
        )}

        <Group justify="flex-end" mt="md" gap="xs">
          <Button variant="default" onClick={handleClose}>
            Cancel
          </Button>

          <Button
            variant="outline"
            color="yellow"
            loading={isSubmitting}
            onClick={() => handleGrade("draft")}
          >
            Save Draft
          </Button>

          <Button
            variant="filled"
            color="green"
            disabled={isTa}
            loading={isSubmitting}
            onClick={() => handleGrade("release")}
          >
            Release Grade
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

export default GradingModal;
