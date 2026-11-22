import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Divider,
  FileInput,
  Group,
  Modal,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import {
  TbAlertCircle,
  TbCheck,
  TbClock,
  TbDownload,
  TbFile,
  TbFileText,
  TbLink,
  TbUpload,
} from "react-icons/tb";

import {
  downloadSubmissionFile,
  submitAssignment,
  useMySubmission,
} from "../api/hooks";
import type {
  CourseAssignment,
  SubmissionType,
} from "../api/types";

interface StudentSubmissionModalProps {
  opened: boolean;
  onClose: () => void;
  workspaceId: number;
  assignment: CourseAssignment | null;
  onSuccess?: () => void;
}

export function StudentSubmissionModal({
  opened,
  onClose,
  workspaceId,
  assignment,
  onSuccess,
}: StudentSubmissionModalProps) {
  const assignmentId = assignment?.id ?? null;
  const { data: mySubmission, loading: loadingSubmission, refetch } = useMySubmission(
    workspaceId,
    assignmentId,
  );

  const [submissionType, setSubmissionType] = useState<SubmissionType>("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (opened) {
      refetch();
      setError(null);
      setSuccessMsg(null);
      setSelectedFile(null);
      setTextContent("");
      setLinkUrl("");
      setSubmissionType("file");
    }
  }, [opened, refetch]);

  if (!assignment) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (submissionType === "file" && !selectedFile) {
      setError("Please select a file to upload.");
      return;
    }
    if (submissionType === "text" && !textContent.trim()) {
      setError("Please enter your submission text.");
      return;
    }
    if (submissionType === "link" && !linkUrl.trim()) {
      setError("Please provide a valid submission URL.");
      return;
    }

    setSubmitting(true);
    try {
      await submitAssignment(workspaceId, assignment.id, {
        submission_type: submissionType,
        file: selectedFile,
        content: textContent.trim(),
        link_url: linkUrl.trim(),
      });
      setSuccessMsg("Assignment work successfully submitted!");
      setSelectedFile(null);
      setTextContent("");
      setLinkUrl("");
      refetch();
      onSuccess?.();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to submit assignment.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadExisting = async () => {
    if (!mySubmission) return;
    setDownloading(true);
    try {
      await downloadSubmissionFile(
        workspaceId,
        assignment.id,
        mySubmission.id,
        mySubmission.filename,
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to download file.");
    } finally {
      setDownloading(false);
    }
  };

  const formattedDeadline = assignment.due_at
    ? new Date(assignment.due_at).toLocaleString()
    : "No deadline";

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs">
          <Title order={5}>Submit Assignment: {assignment.title}</Title>
        </Group>
      }
      size="lg"
    >
      <Stack gap="md">
        {/* Deadline & Status Banner */}
        <Paper withBorder p="sm" bg="#f8f9fa" radius="sm">
          <Group justify="space-between" align="center" wrap="wrap">
            <Group gap="xs">
              <TbClock size={16} color="gray" />
              <Text size="sm" fw={500}>
                Deadline: {formattedDeadline}
              </Text>
            </Group>
            {assignment.due_at && (
              assignment.has_passed ? (
                <Badge color="red" variant="filled" leftSection={<TbAlertCircle size={12} />}>
                  Deadline Passed (Late Submission)
                </Badge>
              ) : (
                <Badge color="teal" variant="light" leftSection={<TbCheck size={12} />}>
                  Deadline Active
                </Badge>
              )
            )}
          </Group>
        </Paper>

        {assignment.instructions && (
          <div>
            <Text size="xs" fw={600} c="dimmed" mb={4}>
              Instructions:
            </Text>
            <Text
              size="sm"
              style={{
                whiteSpace: "pre-line",
                lineHeight: 1.5,
                background: "#fdfdfd",
                padding: "8px",
                border: "1px solid #e9ecef",
                borderRadius: "4px",
              }}
            >
              {assignment.instructions}
            </Text>
          </div>
        )}

        {/* Existing Submission Details */}
        {mySubmission && (
          <Paper withBorder p="md" radius="sm" style={{ borderColor: "#40c057" }}>
            <Group justify="space-between" mb="xs">
              <Group gap="xs">
                <TbCheck size={18} color="green" />
                <Text fw={600} size="sm">
                  Your Current Submission (Attempt #{mySubmission.attempt_number})
                </Text>
              </Group>
              {mySubmission.is_late ? (
                <Badge color="red" variant="filled">
                  Submitted Late
                </Badge>
              ) : (
                <Badge color="green" variant="light">
                  Submitted On Time
                </Badge>
              )}
            </Group>

            <Text size="xs" c="dimmed" mb="xs">
              Submitted at: {new Date(mySubmission.submitted_at).toLocaleString()}
            </Text>

            {mySubmission.submission_type === "file" && (
              <Group gap="sm" mt="xs">
                <TbFile size={16} />
                <Text size="sm" fw={500}>
                  {mySubmission.filename} ({(mySubmission.file_size / 1024).toFixed(1)} KB)
                </Text>
                <Button
                  size="xs"
                  variant="light"
                  leftSection={<TbDownload size={14} />}
                  onClick={handleDownloadExisting}
                  loading={downloading}
                >
                  Download
                </Button>
              </Group>
            )}

            {mySubmission.submission_type === "link" && (
              <Group gap="sm" mt="xs">
                <TbLink size={16} />
                <Text
                  component="a"
                  href={mySubmission.link_url}
                  target="_blank"
                  rel="noreferrer"
                  size="sm"
                  c="blue"
                >
                  {mySubmission.link_url}
                </Text>
              </Group>
            )}

            {mySubmission.submission_type === "text" && (
              <Paper withBorder p="xs" mt="xs" bg="#fafafa">
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {mySubmission.content}
                </Text>
              </Paper>
            )}

            {/* Evaluation & Grade Feedback (BR-LMS-016, BR-LMS-018, UC-LMS-014) */}
            {mySubmission.grade ? (
              <Paper withBorder p="sm" mt="sm" bg="#f0fdf4" style={{ borderColor: "#86efac" }} radius="xs">
                <Group justify="space-between" align="center" mb={6}>
                  <Group gap="xs">
                    <Text size="xs" fw={700} c="green.9" tt="uppercase">
                      Grade & Evaluation
                    </Text>
                    <Badge color="green" size="xs" variant="filled">
                      Released
                    </Badge>
                  </Group>
                  <Badge size="md" color="green" variant="light">
                    Score: {mySubmission.grade.score} / {assignment.max_points ?? 100}
                  </Badge>
                </Group>
                {mySubmission.grade.feedback ? (
                  <div>
                    <Text size="xs" fw={600} c="dimmed" mb={2}>
                      Feedback:
                    </Text>
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                      {mySubmission.grade.feedback}
                    </Text>
                  </div>
                ) : (
                  <Text size="xs" c="dimmed" fs="italic">
                    No written feedback provided.
                  </Text>
                )}
                <Text size="xs" c="dimmed" mt={6}>
                  Evaluated by {mySubmission.grade.grader_name}
                  {mySubmission.grade.released_at && ` • Released ${new Date(mySubmission.grade.released_at).toLocaleDateString()}`}
                </Text>
              </Paper>
            ) : (
              <Paper withBorder p="xs" mt="sm" bg="#f8f9fa" radius="xs">
                <Group justify="space-between" align="center">
                  <Text size="xs" c="dimmed">
                    Evaluation:
                  </Text>
                  <Badge color="gray" size="xs" variant="light">
                    Grade Pending Release
                  </Badge>
                </Group>
              </Paper>
            )}
          </Paper>
        )}

        <Divider label={mySubmission ? "Resubmit or Replace Work" : "Submit Your Work"} labelPosition="center" />

        {error && (
          <Alert color="red" title="Error" icon={<TbAlertCircle size={16} />}>
            {error}
          </Alert>
        )}

        {successMsg && (
          <Alert color="green" title="Success" icon={<TbCheck size={16} />}>
            {successMsg}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <div>
              <Text size="xs" fw={600} c="dimmed" mb={4}>
                Submission Type:
              </Text>
              <SegmentedControl
                value={submissionType}
                onChange={(val) => setSubmissionType(val as SubmissionType)}
                data={[
                  { label: "File Upload", value: "file" },
                  { label: "Text Response", value: "text" },
                  { label: "External Link", value: "link" },
                ]}
                fullWidth
              />
            </div>

            {submissionType === "file" && (
              <FileInput
                label="Select File"
                placeholder="Choose PDF, code, archive, or report file"
                leftSection={<TbUpload size={16} />}
                value={selectedFile}
                onChange={setSelectedFile}
                clearable
                description="Max file size 25 MB. Executables and scripts (.exe, .sh, .bat) are disallowed."
                required
              />
            )}

            {submissionType === "link" && (
              <TextInput
                label="Submission Link URL"
                placeholder="https://github.com/..."
                leftSection={<TbLink size={16} />}
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.currentTarget.value)}
                required
                description="Enter a valid http:// or https:// URL to your repository or work."
              />
            )}

            {submissionType === "text" && (
              <Textarea
                label="Submission Text"
                placeholder="Type or paste your solution, proof, or answers here..."
                leftSection={<TbFileText size={16} />}
                value={textContent}
                onChange={(e) => setTextContent(e.currentTarget.value)}
                minRows={5}
                autosize
                required
              />
            )}

            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={onClose} disabled={submitting}>
                Close
              </Button>
              <Button type="submit" loading={submitting || loadingSubmission}>
                {mySubmission ? "Submit Revision" : "Submit Assignment"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Stack>
    </Modal>
  );
}
