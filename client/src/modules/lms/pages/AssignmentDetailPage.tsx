import { useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  FileInput,
  Grid,
  Group,
  Modal,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaArrowLeft,
  FaCheckCircle,
  FaClipboardCheck,
  FaClock,
  FaExclamationTriangle,
  FaExternalLinkAlt,
  FaFileAlt,
  FaFileDownload,
  FaHistory,
  FaLock,
  FaPaperPlane,
  FaPen,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAssignment,
  useAssignmentSubmissions,
  useGradeAuditLogs,
  useGradeSubmission,
  useReleaseGrades,
  useSubmitAssignment,
} from "../api/hooks";
import type { AssignmentSubmission } from "../api/types";

export default function AssignmentDetailPage({ assignmentIdProp }: { assignmentIdProp?: number } = {}) {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const [searchParams] = useSearchParams();
  const id = assignmentIdProp ?? Number(assignmentId || searchParams.get("assignmentId"));
  const navigate = useNavigate();
  const { session } = useAuth();
  const user = session?.user;

  const { data: assignment, isPending: asgnPending, error: asgnError } = useAssignment(id);
  const { data: submissions, isPending: subsPending } = useAssignmentSubmissions(id);

  const submitAssignment = useSubmitAssignment(id);
  const gradeSubmission = useGradeSubmission(0, id);
  const releaseGrades = useReleaseGrades(id);

  // Student submission form state
  const [submissionText, setSubmissionText] = useState("");
  const [submissionLink, setSubmissionLink] = useState("");
  const [submissionFile, setSubmissionFile] = useState<File | null>(null);

  // Grading modal state
  const [gradingModalOpen, setGradingModalOpen] = useState(false);
  const [selectedSub, setSelectedSub] = useState<AssignmentSubmission | null>(null);
  const [pointsAwarded, setPointsAwarded] = useState<number>(0);
  const [feedback, setFeedback] = useState("");
  const [changeReason, setChangeReason] = useState("");

  // Audit modal state
  const [auditGradeId, setAuditGradeId] = useState<number | null>(null);
  const { data: auditLogs, isPending: auditPending } = useGradeAuditLogs(auditGradeId || 0);

  // Release grades confirmation modal
  const [releaseModalOpen, setReleaseModalOpen] = useState(false);

  if (asgnError) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={asgnError} />
      </Container>
    );
  }

  if (asgnPending || !assignment) {
    return (
      <Container size="lg" py="md">
        <Text c="dimmed">Loading assignment details...</Text>
      </Container>
    );
  }

  const dueDate = new Date(assignment.due_date);
  const isPastDue = new Date() > dueDate;
  const mySub = assignment.my_submission;

  const handleSubmit = () => {
    if (assignment.submission_type === "file" && submissionFile) {
      const formData = new FormData();
      formData.append("submission_type", "file");
      formData.append("file_submission", submissionFile);
      submitAssignment.mutate(formData, {
        onSuccess: () => {
          notifications.show({
            title: "Assignment submitted",
            message: "Your submission file has been uploaded.",
            color: "green",
          });
          setSubmissionFile(null);
        },
        onError: (err) => {
          notifications.show({
            title: "Submission failed",
            message: errorMessage(err),
            color: "red",
          });
        },
      });
    } else {
      submitAssignment.mutate(
        {
          submission_type: assignment.submission_type,
          text_response: submissionText,
          link_url: submissionLink,
        },
        {
          onSuccess: () => {
            notifications.show({
              title: "Assignment submitted",
              message: "Your response has been saved.",
              color: "green",
            });
            setSubmissionText("");
            setSubmissionLink("");
          },
          onError: (err) => {
            notifications.show({
              title: "Submission failed",
              message: errorMessage(err),
              color: "red",
            });
          },
        },
      );
    }
  };

  const openGradingModal = (sub: AssignmentSubmission) => {
    setSelectedSub(sub);
    setPointsAwarded(sub.grade ? Number(sub.grade.points_awarded) : 0);
    setFeedback(sub.grade?.feedback || "");
    setChangeReason("");
    setGradingModalOpen(true);
  };

  const handleSaveGrade = () => {
    if (!selectedSub) return;
    gradeSubmission.mutate(
      {
        points_awarded: pointsAwarded,
        feedback: feedback.trim(),
        change_reason: changeReason.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Grade recorded",
            message: "Evaluation score and feedback saved.",
            color: "green",
          });
          setGradingModalOpen(false);
          setSelectedSub(null);
        },
        onError: (err) => {
          notifications.show({
            title: "Grading error",
            message: errorMessage(err),
            color: "red",
          });
        },
      },
    );
  };

  const handleReleaseGrades = () => {
    releaseGrades.mutate(undefined, {
      onSuccess: (data) => {
        notifications.show({
          title: "Grades released",
          message: data.message || `Published ${data.released_count} grades to students.`,
          color: "green",
        });
        setReleaseModalOpen(false);
      },
      onError: (err) => {
        notifications.show({
          title: "Release failed",
          message: errorMessage(err),
          color: "red",
        });
      },
    });
  };

  return (
    <Container size="lg" py="md">
      <Button
        variant="subtle"
        size="xs"
        leftSection={<FaArrowLeft size={12} />}
        onClick={() => navigate(`/lms/courses?courseId=${assignment.course}`)}
        mb="xs"
      >
        Back to {assignment.course_code || "Course Workspace"}
      </Button>

      {/* Assignment Header Card */}
      <Card withBorder padding="lg" radius="md" mb="lg">
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <div>
            <Group gap="xs" mb={4}>
              <Badge variant="filled" color="indigo" size="sm">
                {assignment.course_code}
              </Badge>
              <StatusBadge status={assignment.status} />
              <Badge variant="outline" color="gray" size="sm">
                {assignment.submission_type.toUpperCase()}
              </Badge>
            </Group>
            <Title order={2}>{assignment.title}</Title>
            <Text size="sm" c="dimmed" mt={2}>
              {assignment.course_name}
            </Text>
          </div>

          <Group gap="md">
            <Card withBorder padding="xs" radius="sm">
              <Text size="xs" c="dimmed">
                Points Possible
              </Text>
              <Text fw={700} size="lg" c="indigo">
                {assignment.points_possible}
              </Text>
            </Card>
            <Card withBorder padding="xs" radius="sm">
              <Text size="xs" c="dimmed">
                Due Date
              </Text>
              <Text fw={700} size="sm" c={isPastDue ? "red" : undefined}>
                {dueDate.toLocaleString()}
              </Text>
            </Card>
          </Group>
        </Group>

        <Divider my="md" />

        <Box mb="md">
          <Text fw={600} size="sm" mb="xs">
            Instructions &amp; Requirements
          </Text>
          <Paper withBorder p="md" bg="var(--mantine-color-gray-0)">
            <Text style={{ whiteSpace: "pre-wrap" }} size="sm">
              {assignment.instructions}
            </Text>
          </Paper>
        </Box>

        <Group justify="space-between">
          <Text size="xs" c="dimmed">
            Late Submissions:{" "}
            <strong>
              {assignment.allow_late_submissions ? "Accepted (flagged as Late)" : "Not Accepted"}
            </strong>
          </Text>
        </Group>
      </Card>

      {/* Student Submission Card */}
      {(!submissions || submissions.length === 0) && (
        <Card withBorder padding="lg" radius="md" mb="lg">
          <Title order={4} mb="sm">
            Your Submission
          </Title>

          {mySub ? (
            <Stack gap="sm">
              <Card withBorder padding="md" radius="sm" bg="var(--mantine-color-teal-0)">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Group gap="xs" mb={4}>
                      <Badge color="green" size="sm" leftSection={<FaCheckCircle size={10} />}>
                        SUBMITTED
                      </Badge>
                      {mySub.status === "late" && (
                        <Badge color="orange" size="sm">
                          LATE SUBMISSION
                        </Badge>
                      )}
                      <Text size="xs" c="dimmed">
                        Version {mySub.version}
                      </Text>
                    </Group>
                    <Text size="xs" c="dimmed">
                      Submitted on: {new Date(mySub.submitted_at).toLocaleString()}
                    </Text>
                  </div>
                </Group>

                <Box mt="sm">
                  {mySub.submission_type === "text" && (
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                      {mySub.text_response}
                    </Text>
                  )}
                  {mySub.submission_type === "link" && (
                    <Button
                      component="a"
                      href={mySub.link_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      size="xs"
                      variant="light"
                      leftSection={<FaExternalLinkAlt size={11} />}
                    >
                      {mySub.link_url}
                    </Button>
                  )}
                  {mySub.submission_type === "file" && (
                    <Button
                      component="a"
                      href={`/media/lms/submissions/${mySub.file_name}`}
                      download
                      size="xs"
                      variant="light"
                      leftSection={<FaFileDownload size={11} />}
                    >
                      Download Submitted File ({mySub.file_name})
                    </Button>
                  )}
                </Box>
              </Card>

              {/* Grade Report */}
              {mySub.grade ? (
                <Card withBorder padding="md" radius="sm">
                  <Title order={5} mb="xs" c="indigo">
                    Evaluation &amp; Feedback
                  </Title>
                  <Group justify="space-between" mb="xs">
                    <Text size="sm">
                      Score:{" "}
                      <strong>
                        {mySub.grade.points_awarded} / {assignment.points_possible}
                      </strong>
                    </Text>
                    <Badge color="green" size="sm">
                      RELEASED
                    </Badge>
                  </Group>
                  <Text size="xs" c="dimmed" mb="xs">
                    Graded by {mySub.grade.graded_by_name} ({mySub.grade.graded_by_role.toUpperCase()})
                  </Text>
                  <Divider mb="xs" />
                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                    {mySub.grade.feedback || "No textual feedback provided."}
                  </Text>
                </Card>
              ) : (
                <Card withBorder padding="sm" radius="sm">
                  <Text size="xs" c="dimmed">
                    Grading Status: <strong>Pending review</strong>
                  </Text>
                </Card>
              )}
            </Stack>
          ) : (
            <div>
              {isPastDue && !assignment.allow_late_submissions ? (
                <Card withBorder padding="md" bg="var(--mantine-color-red-0)">
                  <Group gap="sm">
                    <FaLock size={20} color="var(--mantine-color-red-6)" />
                    <div>
                      <Text fw={600} size="sm" c="red">
                        Submissions Closed
                      </Text>
                      <Text size="xs" c="dimmed">
                        The deadline has passed and late submissions are not allowed for this assignment.
                      </Text>
                    </div>
                  </Group>
                </Card>
              ) : (
                <Stack gap="md">
                  {isPastDue && (
                    <Badge color="orange" size="sm" leftSection={<FaClock size={10} />}>
                      Past Deadline - Submission will be marked as Late (BR-LMS-012)
                    </Badge>
                  )}

                  {assignment.submission_type === "text" && (
                    <Textarea
                      label="Your Text Response"
                      placeholder="Type or paste your solution here..."
                      rows={5}
                      required
                      value={submissionText}
                      onChange={(e) => setSubmissionText(e.currentTarget.value)}
                    />
                  )}

                  {assignment.submission_type === "link" && (
                    <TextInput
                      label="Submission URL"
                      placeholder="https://github.com/..."
                      required
                      value={submissionLink}
                      onChange={(e) => setSubmissionLink(e.currentTarget.value)}
                    />
                  )}

                  {assignment.submission_type === "file" && (
                    <FileInput
                      label="Upload Solution File"
                      placeholder="Choose document, code archive, or PDF..."
                      required
                      value={submissionFile}
                      onChange={setSubmissionFile}
                    />
                  )}

                  <Button
                    leftSection={<FaPaperPlane size={12} />}
                    color="indigo"
                    onClick={handleSubmit}
                    loading={submitAssignment.isPending}
                    disabled={
                      (assignment.submission_type === "text" && !submissionText.trim()) ||
                      (assignment.submission_type === "link" && !submissionLink.trim()) ||
                      (assignment.submission_type === "file" && !submissionFile)
                    }
                  >
                    Submit Assignment
                  </Button>
                </Stack>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Faculty / TA Submissions Table */}
      {submissions && submissions.length >= 0 && (
        <Card withBorder padding="lg" radius="md">
          <Group justify="space-between" mb="md" wrap="wrap">
            <div>
              <Title order={4}>Student Submissions &amp; Evaluation</Title>
              <Text size="xs" c="dimmed">
                Review submissions, record scores, and release final grades to the roster
              </Text>
            </div>
            {user?.kind !== "student" && (
              <Button
                color="green"
                leftSection={<FaClipboardCheck size={14} />}
                onClick={() => setReleaseModalOpen(true)}
                loading={releaseGrades.isPending}
              >
                Release Grades (UC-LMS-013)
              </Button>
            )}
          </Group>

          {subsPending && <Text c="dimmed">Loading submissions...</Text>}

          {!subsPending && submissions.length === 0 && (
            <Card withBorder padding="xl" style={{ textAlign: "center" }}>
              <ThemeIcon size={40} radius="xl" color="gray" variant="light" mb="xs">
                <FaFileAlt size={20} />
              </ThemeIcon>
              <Text fw={600}>No submissions received yet</Text>
              <Text size="xs" c="dimmed">
                Student submissions will appear here once submitted.
              </Text>
            </Card>
          )}

          {submissions.length > 0 && (
            <Table highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Student ID</Table.Th>
                  <Table.Th>Submission Time</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Type / Artifact</Table.Th>
                  <Table.Th>Score</Table.Th>
                  <Table.Th>Grade Status</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {submissions.map((sub) => {
                  const gr = sub.grade;
                  return (
                    <Table.Tr key={sub.id}>
                      <Table.Td>
                        <strong>User #{sub.student_user_id}</strong>
                      </Table.Td>
                      <Table.Td>{new Date(sub.submitted_at).toLocaleString()}</Table.Td>
                      <Table.Td>
                        <Badge color={sub.status === "late" ? "orange" : "teal"} size="xs">
                          {sub.status.toUpperCase()}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {sub.submission_type === "text" && (
                          <Text size="xs" lineClamp={1}>
                            {sub.text_response}
                          </Text>
                        )}
                        {sub.submission_type === "link" && (
                          <Button
                            component="a"
                            href={sub.link_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="subtle"
                            leftSection={<FaExternalLinkAlt size={10} />}
                          >
                            Link
                          </Button>
                        )}
                        {sub.submission_type === "file" && (
                          <Button
                            component="a"
                            href={`/media/lms/submissions/${sub.file_name}`}
                            download
                            size="xs"
                            variant="subtle"
                            leftSection={<FaFileDownload size={10} />}
                          >
                            File ({sub.file_name})
                          </Button>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {gr ? (
                          <Text fw={600} size="sm">
                            {gr.points_awarded} / {assignment.points_possible}
                          </Text>
                        ) : (
                          <Text c="dimmed" size="xs">
                            Not evaluated
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {gr ? (
                          <Badge color={gr.status === "released" ? "green" : "gray"} size="xs">
                            {gr.status.toUpperCase()}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap="xs">
                          <Button
                            size="xs"
                            variant="light"
                            color="indigo"
                            leftSection={<FaPen size={10} />}
                            onClick={() => openGradingModal(sub)}
                          >
                            {gr ? "Edit Grade" : "Evaluate"}
                          </Button>
                          {gr && (
                            <ActionIcon
                              size="sm"
                              variant="subtle"
                              color="gray"
                              title="Audit History"
                              onClick={() => setAuditGradeId(gr.id)}
                            >
                              <FaHistory size={12} />
                            </ActionIcon>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      )}

      {/* Grade Evaluation Modal */}
      <FormModal
        opened={gradingModalOpen}
        onClose={() => setGradingModalOpen(false)}
        title={selectedSub?.grade ? "Edit Evaluation Score" : "Evaluate Submission"}
        subtitle={`Student #${selectedSub?.student_user_id} - Assignment: ${assignment.title}`}
        onSubmit={handleSaveGrade}
        submitLabel="Save Evaluation"
        submitting={gradeSubmission.isPending}
        disabled={
          pointsAwarded < 0 ||
          pointsAwarded > Number(assignment.points_possible) ||
          (selectedSub?.grade?.status === "released" && !changeReason.trim())
        }
        disabledReason={
          selectedSub?.grade?.status === "released" && !changeReason.trim()
            ? "Change reason is mandatory for post-release grade modifications (BR-LMS-019)."
            : "Points awarded must be between 0 and maximum possible points."
        }
      >
        <Stack gap="md">
          {selectedSub?.grade?.status === "released" && (
            <Card withBorder padding="xs" bg="var(--mantine-color-orange-0)">
              <Group gap="xs">
                <FaExclamationTriangle color="var(--mantine-color-orange-7)" size={16} />
                <Text size="xs" c="orange.9">
                  This grade is already RELEASED to the student. Changing it will record a permanent audit entry (BR-LMS-019).
                </Text>
              </Group>
            </Card>
          )}

          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Points Awarded"
                type="number"
                min={0}
                max={Number(assignment.points_possible)}
                required
                value={pointsAwarded}
                onChange={(e) => setPointsAwarded(parseFloat(e.currentTarget.value) || 0)}
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="Max Points Possible"
                disabled
                value={assignment.points_possible}
              />
            </Grid.Col>
          </Grid>

          <Textarea
            label="Evaluation Feedback"
            placeholder="Qualitative comments, rubric details, suggestions..."
            rows={4}
            value={feedback}
            onChange={(e) => setFeedback(e.currentTarget.value)}
          />

          {selectedSub?.grade?.status === "released" && (
            <Textarea
              label="Mandatory Reason for Post-Release Grade Modification"
              placeholder="e.g. Re-evaluated question 3 after student clarification / regrade request"
              required
              rows={2}
              value={changeReason}
              onChange={(e) => setChangeReason(e.currentTarget.value)}
            />
          )}
        </Stack>
      </FormModal>

      {/* Grade Release Confirmation Modal */}
      <Modal
        opened={releaseModalOpen}
        onClose={() => setReleaseModalOpen(false)}
        title="Release Grades to Enrolled Students"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to release all draft grades for <strong>{assignment.title}</strong>?
          </Text>
          <Text size="xs" c="dimmed">
            Once released, evaluation scores and feedback become immediately visible to all students on their gradebooks and assignment portals (CFR-LMS-013).
          </Text>
          <Group justify="flex-end" gap="xs">
            <Button variant="default" onClick={() => setReleaseModalOpen(false)}>
              Cancel
            </Button>
            <Button color="green" onClick={handleReleaseGrades} loading={releaseGrades.isPending}>
              Confirm Release
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Audit History Modal */}
      <Modal
        opened={!!auditGradeId}
        onClose={() => setAuditGradeId(null)}
        title="Grade Change Audit Log (UC-LMS-014 / BR-LMS-019)"
        centered
        size="lg"
      >
        <Stack gap="sm">
          {auditPending && <Text c="dimmed">Loading audit log...</Text>}
          {!auditPending && (!auditLogs || auditLogs.length === 0) && (
            <Text size="sm" c="dimmed">
              No modifications recorded yet. Initial grade release has not been modified.
            </Text>
          )}
          {auditLogs?.map((log) => (
            <Card key={log.id} withBorder padding="sm" radius="sm">
              <Group justify="space-between" mb={2}>
                <Text size="xs" fw={700}>
                  Score Change: {log.previous_points ?? "None"} &rarr; {log.new_points}
                </Text>
                <Text size="xs" c="dimmed">
                  {new Date(log.changed_at).toLocaleString()}
                </Text>
              </Group>
              <Text size="xs" c="dimmed">
                Modified by: <strong>{log.changed_by_name || `User #${log.changed_by_user_id}`}</strong>
              </Text>
              <Divider my={4} />
              <Text size="xs">
                <strong>Reason:</strong> {log.change_reason}
              </Text>
            </Card>
          ))}
        </Stack>
      </Modal>
    </Container>
  );
}
