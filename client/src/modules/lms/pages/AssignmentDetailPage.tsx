import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaCheckCircle, FaExclamationCircle, FaUpload } from "react-icons/fa";
import { useParams } from "react-router-dom";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAssignmentSubmissions, useSubmitAssignment } from "../api/hooks";

export default function AssignmentDetailPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const id = Number(assignmentId);

  const { data: submissions } = useAssignmentSubmissions(id);
  const submitMutation = useSubmitAssignment(id);

  const [submissionType, setSubmissionType] = useState<string>("text");
  const [submissionContent, setSubmissionContent] = useState("");

  const latestSubmission = submissions && submissions.length > 0 ? submissions[0] : null;

  const handleSubmit = async () => {
    if (!submissionContent.trim()) {
      notifications.show({
        color: "red",
        message: "Please provide your submission text or file URL.",
      });
      return;
    }

    try {
      await submitMutation.mutateAsync({
        submission_type: submissionType,
        submission_content: submissionContent,
      });
      notifications.show({
        color: "green",
        message: "Assignment submitted successfully!",
      });
      setSubmissionContent("");
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  return (
    <Container size="md" py="md">
      <PageHeader
        title={latestSubmission ? latestSubmission.assignment_title : `Assignment #${id}`}
        subtitle="Submit your deliverable and view released evaluations"
      />

      <Stack gap="lg">
        {/* Previous Submission Status */}
        {latestSubmission ? (
          <Card withBorder p="md" radius="sm">
            <Group justify="space-between" mb="xs">
              <Title order={5}>Your Submission Status</Title>
              <Badge color={latestSubmission.status === "late" ? "orange" : "green"}>
                {latestSubmission.status.toUpperCase()}
              </Badge>
            </Group>
            <Text size="sm" c="dimmed">
              Submitted at: {new Date(latestSubmission.submitted_at).toLocaleString()}
            </Text>
            <Text size="sm" mt="xs">
              <strong>Content:</strong> {latestSubmission.submission_content}
            </Text>

            {/* Grade Display */}
            {latestSubmission.grade && latestSubmission.grade.status === "released" ? (
              <Alert icon={<FaCheckCircle />} color="green" mt="md" title="Released Evaluation">
                <Text size="sm" fw={600}>
                  Score: {latestSubmission.grade.points} pts
                </Text>
                {latestSubmission.grade.feedback && (
                  <Text size="sm" mt="xs">
                    Feedback: {latestSubmission.grade.feedback}
                  </Text>
                )}
              </Alert>
            ) : (
              <Alert icon={<FaExclamationCircle />} color="blue" mt="md">
                Submission received. Evaluation is currently in progress.
              </Alert>
            )}
          </Card>
        ) : (
          <Alert color="gray">No submission recorded for this assignment yet.</Alert>
        )}

        {/* Submit Form */}
        <Card withBorder p="lg" radius="sm">
          <Title order={4} mb="md">
            Submit Deliverable
          </Title>
          <Stack gap="md">
            <Select
              label="Submission Type"
              value={submissionType}
              onChange={(val) => setSubmissionType(val || "text")}
              data={[
                { value: "text", label: "Text Entry" },
                { value: "file", label: "File Document (URL/Path)" },
                { value: "link", label: "Repository / Online Link" },
              ]}
            />
            <Textarea
              label="Deliverable Content"
              description="Enter your response text, file download URL, or link"
              placeholder="Paste submission link or type solution here..."
              minRows={4}
              value={submissionContent}
              onChange={(e) => setSubmissionContent(e.currentTarget.value)}
            />
            <Button
              leftSection={<FaUpload />}
              color="blue"
              onClick={handleSubmit}
              loading={submitMutation.isPending}
            >
              Submit Assignment
            </Button>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
