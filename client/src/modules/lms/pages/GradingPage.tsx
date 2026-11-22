import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Drawer,
  Group,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaEdit, FaHistory, FaPaperPlane } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAssignments,
  useCourses,
  useGradeAudits,
  useGradeSubmission,
  usePublishGrades,
  useSubmissions,
  useUpdateGrade,
} from "../api/hooks";
import type { AssignmentSubmission } from "../api/types";

export default function GradingPage() {
  const { data: courses } = useCourses();
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const activeCourseId = selectedCourseId ?? courses?.[0]?.course_id ?? null;

  const { data: assignments } = useAssignments(activeCourseId);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number | null>(null);
  const activeAssignmentId = selectedAssignmentId ?? assignments?.[0]?.id ?? null;

  const { data: submissions, isPending, error } = useSubmissions(activeAssignmentId);
  const gradeSubmission = useGradeSubmission();
  const updateGrade = useUpdateGrade();
  const publishGrades = usePublishGrades();
  const { can } = useAuth();

  const canPublishGrades = can("lms.grade.publish");

  // Grading modal state
  const [gradingSub, setGradingSub] = useState<AssignmentSubmission | null>(null);
  const [pointsAwarded, setPointsAwarded] = useState("85.00");
  const [feedbackText, setFeedbackText] = useState("");
  const [reason, setReason] = useState("");
  const [isEditMode, setIsEditMode] = useState(false);

  // Audit history drawer state
  const [auditSubId, setAuditSubId] = useState<number | null>(null);
  const { data: audits, isPending: isAuditsPending } = useGradeAudits(auditSubId);

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  const courseOptions = (courses ?? []).map((c) => ({
    value: String(c.course_id),
    label: `${c.course_code}: ${c.title}`,
  }));

  const assignmentOptions = (assignments ?? []).map((a) => ({
    value: String(a.id),
    label: `${a.title} (${a.points_possible} pts)`,
  }));

  const handleSaveGrade = () => {
    if (!gradingSub) return;

    if (isEditMode) {
      updateGrade.mutate(
        {
          submissionId: gradingSub.id,
          points_awarded: pointsAwarded,
          feedback_text: feedbackText,
          reason,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Grade Updated",
              message: "Submission grade has been updated.",
            });
            setGradingSub(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Update Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else {
      gradeSubmission.mutate(
        {
          submissionId: gradingSub.id,
          points_awarded: pointsAwarded,
          feedback_text: feedbackText,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Grade Saved",
              message: "Draft grade saved successfully.",
            });
            setGradingSub(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Grading Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    }
  };

  const handlePublishAll = () => {
    if (!activeAssignmentId) return;
    if (confirm("Are you sure you want to publish all draft grades to enrolled students?")) {
      publishGrades.mutate(
        { assignmentId: activeAssignmentId },
        {
          onSuccess: (res) => {
            notifications.show({
              color: "green",
              title: "Grades Published",
              message: `Published grades for ${res.published_count} submission(s).`,
            });
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Publish Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Submissions & Grading"
        subtitle="Evaluate student work, manage feedback, and publish grades"
        action={
          canPublishGrades && activeAssignmentId ? (
            <Button
              color="teal"
              leftSection={<FaPaperPlane size={12} />}
              onClick={handlePublishAll}
              loading={publishGrades.isPending}
            >
              Publish Draft Grades
            </Button>
          ) : undefined
        }
      />

      <Group grow mb="lg">
        {courseOptions.length > 0 && (
          <Select
            label="Select Course"
            data={courseOptions}
            value={activeCourseId ? String(activeCourseId) : null}
            onChange={(val) => {
              setSelectedCourseId(val ? Number(val) : null);
              setSelectedAssignmentId(null);
            }}
            allowDeselect={false}
          />
        )}

        {assignmentOptions.length > 0 && (
          <Select
            label="Select Assignment"
            data={assignmentOptions}
            value={activeAssignmentId ? String(activeAssignmentId) : null}
            onChange={(val) => setSelectedAssignmentId(val ? Number(val) : null)}
            allowDeselect={false}
          />
        )}
      </Group>

      {isPending && <Text c="dimmed">Loading student submissions…</Text>}

      {!isPending && (!submissions || submissions.length === 0) && (
        <Card padding="xl" withBorder>
          <Text fw={600} ta="center">
            No submissions found for this assignment
          </Text>
        </Card>
      )}

      {submissions && submissions.length > 0 && (
        <Card padding={0} withBorder>
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Student</Table.Th>
                <Table.Th>Format</Table.Th>
                <Table.Th>Submitted At</Table.Th>
                <Table.Th>Standing</Table.Th>
                <Table.Th>Attempt</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {submissions.map((sub) => (
                <Table.Tr key={sub.id}>
                  <Table.Td>
                    <Text fw={600} size="sm">
                      User {sub.student_id}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" size="xs">
                      {sub.submission_type}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">
                      {new Date(sub.submitted_at).toLocaleString()}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={sub.status === "SUBMITTED" ? "green" : "red"} size="sm">
                      {sub.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">#{sub.attempt_number}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<FaCheck size={10} />}
                        onClick={() => {
                          setGradingSub(sub);
                          setIsEditMode(false);
                          setPointsAwarded("85.00");
                          setFeedbackText("");
                          setReason("");
                        }}
                      >
                        Grade
                      </Button>
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<FaEdit size={10} />}
                        onClick={() => {
                          setGradingSub(sub);
                          setIsEditMode(true);
                          setPointsAwarded("90.00");
                          setFeedbackText("");
                          setReason("Recheck requested");
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        size="xs"
                        variant="subtle"
                        color="gray"
                        leftSection={<FaHistory size={10} />}
                        onClick={() => setAuditSubId(sub.id)}
                      >
                        Audits
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {/* Grade / Edit Grade Modal */}
      <FormModal
        opened={gradingSub != null}
        onClose={() => setGradingSub(null)}
        title={isEditMode ? "Edit Submission Grade" : "Enter Submission Grade"}
        subtitle={`Grading work from Student (User ${gradingSub?.student_id ?? ""})`}
        onSubmit={handleSaveGrade}
        submitting={gradeSubmission.isPending || updateGrade.isPending}
        submitLabel={isEditMode ? "Update Grade" : "Save Draft Grade"}
      >
        <Stack gap="md">
          <TextInput
            label="Points Awarded"
            type="number"
            step="0.5"
            required
            value={pointsAwarded}
            onChange={(e) => setPointsAwarded(e.currentTarget.value)}
          />
          <Textarea
            label="Feedback"
            placeholder="Feedback comments for the student..."
            autosize
            minRows={3}
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.currentTarget.value)}
          />
          {isEditMode && (
            <TextInput
              label="Reason for Grade Change"
              placeholder="e.g. Recheck approved for question 2"
              required
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
            />
          )}
        </Stack>
      </FormModal>

      {/* Grade Audit History Drawer */}
      <Drawer
        opened={auditSubId != null}
        onClose={() => setAuditSubId(null)}
        title="Grade Change Audit History"
        position="right"
        size="md"
      >
        <Stack gap="md">
          {isAuditsPending && <Text c="dimmed">Loading audit trail…</Text>}

          {!isAuditsPending && (!audits || audits.length === 0) && (
            <Text c="dimmed" size="sm">
              No post-release grade modifications have been recorded for this submission.
            </Text>
          )}

          {(audits ?? []).map((audit) => (
            <Card key={audit.id} padding="sm" withBorder>
              <Stack gap={4}>
                <Group justify="space-between">
                  <Badge variant="light">
                    Score: {audit.old_points} → {audit.new_points}
                  </Badge>
                  <Text size="xs" c="dimmed">
                    {new Date(audit.changed_at).toLocaleString()}
                  </Text>
                </Group>
                <Text size="xs" fw={500}>
                  Changed by User {audit.changed_by}
                </Text>
                {audit.reason && (
                  <Text size="xs" c="dimmed">
                    Reason: {audit.reason}
                  </Text>
                )}
                {audit.new_feedback && (
                  <Text size="xs" mt={2}>
                    Updated Feedback: {audit.new_feedback}
                  </Text>
                )}
              </Stack>
            </Card>
          ))}
        </Stack>
      </Drawer>
    </Container>
  );
}
