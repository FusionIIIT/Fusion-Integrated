import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Center,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  getFileDownloadUrl,
  useAssignment,
  useAssignmentSubmissions,
  useGrades,
} from "../api/hooks";
import { SubmissionModal } from "../components/SubmissionModal";

export const StudentAssignmentDetailPage: React.FC = () => {
  const { assignmentId: paramAssignmentId } = useParams<{ assignmentId: string }>();
  const assignmentId = paramAssignmentId ? parseInt(paramAssignmentId) : 0;

  const [submitModalOpened, setSubmitModalOpened] = useState(false);

  const {
    data: assignment,
    isLoading: assignmentLoading,
    error: assignmentError,
  } = useAssignment(assignmentId);

  const {
    data: submissions,
    isLoading: submissionsLoading,
    error: submissionsError,
  } = useAssignmentSubmissions(assignmentId);

  const { data: grades } = useGrades();

  const isLoading = assignmentLoading || submissionsLoading;
  const isError = assignmentError || submissionsError;

  if (isLoading) {
    return (
      <Center py="xl">
        <Loader size="lg" />
      </Center>
    );
  }

  if (isError || !assignment) {
    return (
      <Alert color="red" title="Error">
        Unable to load assignment details.
      </Alert>
    );
  }

  const latestSubmission = submissions && submissions.length > 0
    ? [...submissions].sort((a, b) => b.version - a.version)[0]
    : null;

  const releasedGrade = latestSubmission && grades
    ? grades.find(
        (g) => g.submission === latestSubmission.id && g.released_at !== null && !g.is_draft
      )
    : null;

  return (
    <Stack gap="lg">
      <PageHeader
        title={assignment.title}
        subtitle={`Maximum Points: ${assignment.points_possible} • Submission Mode: ${assignment.submission_type.toUpperCase()}`}
        action={
          <Group gap="xs">
            <Button
              component={Link}
              to={`/courses/${assignment.course}`}
              variant="default"
              size="sm"
            >
              Back to Course
            </Button>
            <Button
              variant="filled"
              size="sm"
              onClick={() => setSubmitModalOpened(true)}
            >
              Submit Assignment
            </Button>
          </Group>
        }
      />

      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" align="center" mb="xs">
          <Badge color={assignment.is_published ? "green" : "yellow"}>
            {assignment.is_published ? "Published" : "Draft"}
          </Badge>
          <Text size="sm" c="dimmed">
            Due: {assignment.due_date ? new Date(assignment.due_date).toLocaleString() : "None"}
          </Text>
        </Group>

        <Title order={4} size="h5" mb="xs">
          Instructions
        </Title>
        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
          {assignment.description || "No specific instructions provided."}
        </Text>
      </Paper>

      {/* Submission Status & Released Grade */}
      <Paper withBorder p="md" radius="md">
        <Title order={4} size="h5" mb="sm">
          Your Submission & Evaluation
        </Title>

        {latestSubmission ? (
          <Stack gap="sm">
            <Group justify="space-between" align="center">
              <Group gap="xs">
                <Text fw={600} size="sm">
                  Version {latestSubmission.version}
                </Text>
                <Badge color={latestSubmission.status === "late" ? "orange" : "blue"}>
                  {latestSubmission.status.toUpperCase()}
                </Badge>
              </Group>
              <Text size="xs" c="dimmed">
                Submitted: {new Date(latestSubmission.submitted_at).toLocaleString()}
              </Text>
            </Group>

            {latestSubmission.submission_type === "text" && latestSubmission.content_text && (
              <Paper withBorder p="xs" bg="gray.0">
                <Text size="xs" style={{ whiteSpace: "pre-wrap" }}>
                  {latestSubmission.content_text}
                </Text>
              </Paper>
            )}

            {latestSubmission.submission_type === "link" && latestSubmission.link_url && (
              <Anchor href={latestSubmission.link_url} target="_blank" rel="noopener noreferrer" size="sm">
                {latestSubmission.link_url} ↗
              </Anchor>
            )}

            {latestSubmission.submission_type === "file" && latestSubmission.file_storage_key && (
              <Button
                component="a"
                href={getFileDownloadUrl(latestSubmission.file_storage_key)}
                download
                variant="light"
                size="xs"
                style={{ width: "fit-content" }}
              >
                Download Submitted File
              </Button>
            )}

            <Divider my="sm" />

            {/* Official Grade Section */}
            {releasedGrade ? (
              <Stack gap="xs">
                <Group justify="space-between" align="center">
                  <Text fw={600} size="sm">
                    Official Grade Released
                  </Text>
                  <Badge color="green" size="lg">
                    {releasedGrade.points_awarded} / {assignment.points_possible} pts
                  </Badge>
                </Group>
                {releasedGrade.feedback_text && (
                  <Text size="sm" c="dimmed">
                    Instructor Feedback: {releasedGrade.feedback_text}
                  </Text>
                )}
              </Stack>
            ) : (
              <Alert color="yellow" title="Evaluation Status">
                Grade Pending Release. Feedback and scores are made visible to students once officially released by the instructor.
              </Alert>
            )}
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            You have not submitted work for this assignment yet. Click "Submit Assignment" above to turn in your work.
          </Text>
        )}
      </Paper>

      {/* Submission Modal */}
      <SubmissionModal
        opened={submitModalOpened}
        onClose={() => setSubmitModalOpened(false)}
        assignment={assignment}
      />
    </Stack>
  );
};

export default StudentAssignmentDetailPage;
