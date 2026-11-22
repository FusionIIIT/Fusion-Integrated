import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Divider,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import {
  TbAlertCircle,
  TbCheck,
  TbDownload,
  TbFile,
  TbFileText,
  TbHistory,
  TbInbox,
  TbLink,
  TbSend,
} from "react-icons/tb";

import {
  downloadSubmissionFile,
  gradeSubmission,
  releaseGrades,
  useAssignmentSubmissions,
  useGradeAudit,
} from "../api/hooks";
import type {
  CourseAssignment,
  CourseSubmission,
} from "../api/types";

interface FacultySubmissionsModalProps {
  opened: boolean;
  onClose: () => void;
  workspaceId: number;
  assignment: CourseAssignment | null;
  viewerRole?: string | null;
}

export function FacultySubmissionsModal({
  opened,
  onClose,
  workspaceId,
  assignment,
  viewerRole,
}: FacultySubmissionsModalProps) {
  const assignmentId = assignment?.id ?? null;
  const { data, loading, error, refetch } = useAssignmentSubmissions(
    workspaceId,
    assignmentId,
  );

  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Grading form state
  const [gradingSub, setGradingSub] = useState<CourseSubmission | null>(null);
  const [gradeScore, setGradeScore] = useState<number | string>("");
  const [gradeFeedback, setGradeFeedback] = useState("");
  const [savingGrade, setSavingGrade] = useState(false);
  const [gradeError, setGradeError] = useState<string | null>(null);

  // Grade Release state
  const [releasing, setReleasing] = useState(false);

  // Audit view state
  const [auditSub, setAuditSub] = useState<CourseSubmission | null>(null);
  const { data: auditLogs, loading: loadingAudit } = useGradeAudit(
    workspaceId,
    assignmentId,
    auditSub?.id ?? null,
  );

  if (!assignment) return null;

  const submissions = data?.results ?? [];
  const maxPts = assignment.max_points ?? 100;
  const isFaculty = viewerRole === "instructor";

  const handleDownload = async (sub: CourseSubmission) => {
    setDownloadingId(sub.id);
    setActionError(null);
    try {
      await downloadSubmissionFile(
        workspaceId,
        assignment.id,
        sub.id,
        sub.filename,
      );
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Failed to download submitted file.",
      );
    } finally {
      setDownloadingId(null);
    }
  };

  const openGradingModal = (sub: CourseSubmission) => {
    setGradingSub(sub);
    setGradeScore(sub.grade ? Number(sub.grade.score) : "");
    setGradeFeedback(sub.grade ? sub.grade.feedback : "");
    setGradeError(null);
  };

  const handleSaveGrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gradingSub) return;
    if (gradeScore === "" || Number(gradeScore) < 0 || Number(gradeScore) > maxPts) {
      setGradeError(`Score must be between 0 and ${maxPts}.`);
      return;
    }

    setSavingGrade(true);
    setGradeError(null);
    try {
      await gradeSubmission(workspaceId, assignment.id, gradingSub.id, {
        score: Number(gradeScore),
        feedback: gradeFeedback.trim(),
      });
      setActionSuccess(`Evaluation saved for ${gradingSub.student_name}.`);
      setGradingSub(null);
      refetch();
    } catch (err: unknown) {
      setGradeError(err instanceof Error ? err.message : "Failed to save grade.");
    } finally {
      setSavingGrade(false);
    }
  };

  const handleReleaseAll = async () => {
    if (!isFaculty) return;
    setReleasing(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await releaseGrades(workspaceId, assignment.id);
      setActionSuccess(`Successfully released ${res.released_count} grade(s) to students.`);
      refetch();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to release grades.");
    } finally {
      setReleasing(false);
    }
  };

  return (
    <>
      <Modal
        opened={opened}
        onClose={onClose}
        title={
          <Group gap="xs">
            <Title order={5}>Submissions & Grading: {assignment.title}</Title>
            <Badge variant="filled" color="blue" size="sm">
              {submissions.length} {submissions.length === 1 ? "Submission" : "Submissions"}
            </Badge>
          </Group>
        }
        size="90%"
      >
        <Stack gap="md">
          {error && (
            <Alert color="red" title="Error" icon={<TbAlertCircle size={16} />}>
              {error}
            </Alert>
          )}

          {actionError && (
            <Alert
              color="red"
              title="Error"
              withCloseButton
              onClose={() => setActionError(null)}
              icon={<TbAlertCircle size={16} />}
            >
              {actionError}
            </Alert>
          )}

          {actionSuccess && (
            <Alert
              color="green"
              title="Success"
              withCloseButton
              onClose={() => setActionSuccess(null)}
              icon={<TbCheck size={16} />}
            >
              {actionSuccess}
            </Alert>
          )}

          <Group justify="space-between" align="center" wrap="wrap">
            <Text size="sm" c="dimmed">
              Points Possible: <Text span fw={600} c="dark">{maxPts}</Text>
            </Text>

            {isFaculty ? (
              <Button
                color="teal"
                size="xs"
                leftSection={<TbSend size={14} />}
                onClick={handleReleaseAll}
                loading={releasing}
                disabled={submissions.length === 0}
              >
                Release All Grades to Students
              </Button>
            ) : (
              <Tooltip label="Only faculty members can release grades (BR-LMS-017)">
                <Badge color="gray" variant="light">
                  Release Reserved for Faculty
                </Badge>
              </Tooltip>
            )}
          </Group>

          {loading && (
            <Group justify="center" py="xl">
              <Loader size="md" />
            </Group>
          )}

          {!loading && submissions.length === 0 && (
            <Paper withBorder p="xl" ta="center" radius="md">
              <Group justify="center" mb="xs">
                <TbInbox size={32} color="gray" />
              </Group>
              <Text fw={500} c="dimmed">
                No submissions recorded yet
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Student submissions for this assignment will appear here once submitted.
              </Text>
            </Paper>
          )}

          {!loading && submissions.length > 0 && (
            <Table striped highlightOnHover withTableBorder withColumnBorders>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Student</Table.Th>
                  <Table.Th>Roll No</Table.Th>
                  <Table.Th>Submitted</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Submission</Table.Th>
                  <Table.Th>Grade / Score</Table.Th>
                  <Table.Th>Release Status</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {submissions.map((sub) => {
                  const submittedDate = new Date(sub.submitted_at).toLocaleString();
                  const grade = sub.grade;

                  return (
                    <Table.Tr key={sub.id}>
                      <Table.Td>
                        <Text size="sm" fw={500}>
                          {sub.student_name}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {sub.student_username || `ID: ${sub.student_id}`}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{submittedDate}</Text>
                      </Table.Td>
                      <Table.Td>
                        {sub.is_late ? (
                          <Badge color="red" size="sm" variant="filled">
                            Late (#{sub.attempt_number})
                          </Badge>
                        ) : (
                          <Badge color="green" size="sm" variant="light">
                            On Time (#{sub.attempt_number})
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {sub.submission_type === "file" && (
                          <Group gap={4}>
                            <TbFile size={14} />
                            <Text size="xs" truncate maw={120}>
                              {sub.filename}
                            </Text>
                            <Button
                              size="compact-xs"
                              variant="subtle"
                              onClick={() => handleDownload(sub)}
                              loading={downloadingId === sub.id}
                            >
                              <TbDownload size={12} />
                            </Button>
                          </Group>
                        )}
                        {sub.submission_type === "link" && (
                          <Group gap={4}>
                            <TbLink size={14} />
                            <Text
                              component="a"
                              href={sub.link_url}
                              target="_blank"
                              rel="noreferrer"
                              size="xs"
                              c="blue"
                              truncate
                              maw={120}
                            >
                              Link
                            </Text>
                          </Group>
                        )}
                        {sub.submission_type === "text" && (
                          <Group gap={4}>
                            <TbFileText size={14} />
                            <Text size="xs" truncate maw={120}>
                              {sub.content}
                            </Text>
                          </Group>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {grade ? (
                          <Text size="sm" fw={600}>
                            {grade.score} / {maxPts}
                          </Text>
                        ) : (
                          <Text size="xs" c="dimmed" fs="italic">
                            Not Graded
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td>
                        {grade ? (
                          grade.status === "released" ? (
                            <Badge color="green" size="sm" variant="filled">
                              Released
                            </Badge>
                          ) : (
                            <Badge color="yellow" size="sm" variant="light">
                              Draft
                            </Badge>
                          )
                        ) : (
                          <Badge color="gray" size="sm" variant="outline">
                            Pending
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4}>
                          <Button
                            size="xs"
                            variant="light"
                            onClick={() => openGradingModal(sub)}
                          >
                            {grade ? "Edit Grade" : "Grade"}
                          </Button>
                          {grade && (
                            <Button
                              size="xs"
                              variant="subtle"
                              color="gray"
                              leftSection={<TbHistory size={12} />}
                              onClick={() => setAuditSub(sub)}
                            >
                              Audit
                            </Button>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={refetch}>
              Refresh
            </Button>
            <Button onClick={onClose}>Done</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Grade / Evaluation Drawer Modal */}
      {gradingSub && (
        <Modal
          opened={Boolean(gradingSub)}
          onClose={() => setGradingSub(null)}
          title={
            <Title order={5}>
              Evaluate: {gradingSub.student_name}
            </Title>
          }
          size="md"
        >
          <form onSubmit={handleSaveGrade}>
            <Stack gap="sm">
              {gradeError && (
                <Alert color="red" icon={<TbAlertCircle size={16} />}>
                  {gradeError}
                </Alert>
              )}

              <Text size="xs" c="dimmed">
                Assignment: {assignment.title} (Max points: {maxPts})
              </Text>

              {gradingSub.grade?.status === "released" && (
                <Alert color="yellow" size="xs">
                  This grade is already released. Changes will be recorded in the post-release audit log (BR-LMS-019).
                </Alert>
              )}

              <NumberInput
                label="Score / Marks"
                placeholder={`0 to ${maxPts}`}
                value={gradeScore}
                onChange={setGradeScore}
                min={0}
                max={Number(maxPts)}
                decimalScale={2}
                required
              />

              <Textarea
                label="Feedback"
                placeholder="Enter constructive feedback for the student..."
                value={gradeFeedback}
                onChange={(e) => setGradeFeedback(e.currentTarget.value)}
                rows={4}
              />

              <Group justify="flex-end" mt="md">
                <Button variant="default" onClick={() => setGradingSub(null)}>
                  Cancel
                </Button>
                <Button type="submit" loading={savingGrade}>
                  Save Grade
                </Button>
              </Group>
            </Stack>
          </form>
        </Modal>
      )}

      {/* Audit Trail Modal (BR-LMS-019) */}
      {auditSub && (
        <Modal
          opened={Boolean(auditSub)}
          onClose={() => setAuditSub(null)}
          title={<Title order={5}>Grade Audit Trail: {auditSub.student_name}</Title>}
          size="lg"
        >
          <Stack gap="sm">
            {loadingAudit && (
              <Group justify="center" py="md">
                <Loader size="sm" />
              </Group>
            )}

            {!loadingAudit && (!auditLogs || auditLogs.length === 0) && (
              <Text size="sm" c="dimmed" ta="center">
                No audit records found.
              </Text>
            )}

            {!loadingAudit && auditLogs && auditLogs.length > 0 && (
              <Table striped withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Timestamp</Table.Th>
                    <Table.Th>Action</Table.Th>
                    <Table.Th>Actor</Table.Th>
                    <Table.Th>Score Transition</Table.Th>
                    <Table.Th>Feedback Changes</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {auditLogs.map((log) => (
                    <Table.Tr key={log.id}>
                      <Table.Td>
                        <Text size="xs">{new Date(log.created_at).toLocaleString()}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Badge
                          size="xs"
                          color={
                            log.action === "released"
                              ? "green"
                              : log.action === "updated_post_release"
                              ? "orange"
                              : "blue"
                          }
                        >
                          {log.action}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{log.actor_name}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">
                          {log.score_before ?? "—"} → {log.score_after ?? "—"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" truncate maw={140}>
                          {log.feedback_after || "—"}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}

            <Group justify="flex-end" mt="sm">
              <Button onClick={() => setAuditSub(null)}>Close</Button>
            </Group>
          </Stack>
        </Modal>
      )}
    </>
  );
}
