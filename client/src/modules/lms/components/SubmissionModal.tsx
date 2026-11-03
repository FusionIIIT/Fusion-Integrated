import React, { useState } from "react";
import {
  Alert,
  Button,
  FileInput,
  Group,
  Modal,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { getApiErrorMessage, useSubmitAssignment, useUploadFile } from "../api/hooks";
import type { Assignment, SubmissionType } from "../api/types";

export interface SubmissionModalProps {
  opened: boolean;
  onClose: () => void;
  assignment: Assignment;
}

export const SubmissionModal: React.FC<SubmissionModalProps> = ({
  opened,
  onClose,
  assignment,
}) => {
  const [submissionType, setSubmissionType] = useState<SubmissionType>(
    assignment.submission_type || "file"
  );
  const [contentText, setContentText] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitMutation = useSubmitAssignment(assignment.id);
  const uploadMutation = useUploadFile();

  const handleClose = () => {
    setErrorMsg(null);
    setContentText("");
    setLinkUrl("");
    setFile(null);
    onClose();
  };

  const handleSubmission = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      let fileStorageKey = "";
      if (submissionType === "file") {
        if (!file) {
          setErrorMsg("Please select a file to upload.");
          setIsSubmitting(false);
          return;
        }
        const uploadResult = await uploadMutation.mutateAsync(file);
        fileStorageKey = uploadResult.storage_key;
      }

      await submitMutation.mutateAsync({
        submission_type: submissionType,
        content_text: submissionType === "text" ? contentText : undefined,
        link_url: submissionType === "link" ? linkUrl : undefined,
        file_storage_key: submissionType === "file" ? fileStorageKey : undefined,
      });

      handleClose();
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal opened={opened} onClose={handleClose} title={`Submit: ${assignment.title}`} size="lg">
      <form onSubmit={handleSubmission}>
        <Stack gap="md">
          {errorMsg && (
            <Alert color="red" title="Submission Status" withCloseButton onClose={() => setErrorMsg(null)}>
              {errorMsg}
            </Alert>
          )}

          <Text size="sm" c="dimmed">
            Maximum Points: {assignment.points_possible} • Due:{" "}
            {assignment.due_date ? new Date(assignment.due_date).toLocaleString() : "None"}
          </Text>

          <SegmentedControl
            value={submissionType}
            onChange={(val) => setSubmissionType(val as SubmissionType)}
            data={[
              { label: "File Upload", value: "file" },
              { label: "Text Entry", value: "text" },
              { label: "Website Link", value: "link" },
            ]}
          />

          {submissionType === "file" && (
            <FileInput
              label="Select Submission File"
              placeholder="Click to browse"
              value={file}
              onChange={setFile}
              required
            />
          )}

          {submissionType === "text" && (
            <Textarea
              label="Text Response"
              placeholder="Type your submission here..."
              minRows={5}
              value={contentText}
              onChange={(e) => setContentText(e.currentTarget.value)}
              required
            />
          )}

          {submissionType === "link" && (
            <TextInput
              label="External Link URL"
              placeholder="https://..."
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.currentTarget.value)}
              required
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              Turn In Assignment
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default SubmissionModal;
