import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Stack,
  Table,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaEdit, FaPaperPlane } from "react-icons/fa";
import { useParams } from "react-router-dom";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAssignmentSubmissions, useGradeSubmission, useReleaseGrades } from "../api/hooks";
import type { StudentSubmission } from "../api/types";

export default function GradingPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const id = Number(assignmentId);

  const { data: submissions, isLoading } = useAssignmentSubmissions(id);
  const gradeMutation = useGradeSubmission(0);
  const releaseMutation = useReleaseGrades(id);

  const [selectedSub, setSelectedSub] = useState<StudentSubmission | null>(null);
  const [points, setPoints] = useState<number | string>(0);
  const [feedback, setFeedback] = useState("");

  const handleOpenGradeModal = (sub: StudentSubmission) => {
    setSelectedSub(sub);
    setPoints(sub.grade ? Number(sub.grade.points) : 0);
    setFeedback(sub.grade ? sub.grade.feedback : "");
  };

  const handleSaveGrade = async () => {
    if (!selectedSub) return;
    try {
      await gradeMutation.mutateAsync({
        points: Number(points),
        feedback,
      });
      notifications.show({
        color: "green",
        message: "Grade recorded in Draft state.",
      });
      setSelectedSub(null);
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  const handleReleaseAll = async () => {
    try {
      const res = await releaseMutation.mutateAsync();
      notifications.show({
        color: "teal",
        message: `Successfully released ${res.released_count} grades to students!`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Grading & Evaluation"
        subtitle={`Assignment #${id} — Review submissions, score drafts, and release feedback`}
      />

      <Group justify="flex-end" mb="md">
        <Button
          leftSection={<FaPaperPlane />}
          color="teal"
          onClick={handleReleaseAll}
          loading={releaseMutation.isPending}
        >
          Release All Draft Grades
        </Button>
      </Group>

      {isLoading ? (
        <Text c="dimmed">Loading submissions...</Text>
      ) : !submissions || submissions.length === 0 ? (
        <Card withBorder p="lg">
          <Text c="dimmed" ta="center">
            No student submissions recorded for this assignment yet.
          </Text>
        </Card>
      ) : (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Student ID</Table.Th>
              <Table.Th>Submission Time</Table.Th>
              <Table.Th>Content</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Grade / Feedback</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {submissions.map((sub) => (
              <Table.Tr key={sub.id}>
                <Table.Td fw={500}>u{sub.student_user_id}</Table.Td>
                <Table.Td>{new Date(sub.submitted_at).toLocaleString()}</Table.Td>
                <Table.Td>
                  <Text lineClamp={1}>{sub.submission_content}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={sub.status === "late" ? "orange" : "green"}>
                    {sub.status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {sub.grade ? (
                    <Group gap="xs">
                      <Text fw={600}>{sub.grade.points} pts</Text>
                      <Badge color={sub.grade.status === "released" ? "teal" : "gray"}>
                        {sub.grade.status.toUpperCase()}
                      </Badge>
                    </Group>
                  ) : (
                    <Text c="dimmed">Ungraded</Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<FaEdit />}
                    onClick={() => handleOpenGradeModal(sub)}
                  >
                    Grade
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* Grade Modal */}
      <Modal
        opened={!!selectedSub}
        onClose={() => setSelectedSub(null)}
        title={`Grade Submission — u${selectedSub?.student_user_id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            <strong>Submitted Content:</strong> {selectedSub?.submission_content}
          </Text>
          <NumberInput
            label="Points"
            value={points}
            onChange={(val) => setPoints(val)}
            min={0}
            step={0.5}
          />
          <Textarea
            label="Evaluation Feedback"
            value={feedback}
            onChange={(e) => setFeedback(e.currentTarget.value)}
            minRows={3}
          />
          <Button color="blue" onClick={handleSaveGrade} loading={gradeMutation.isPending}>
            Save Grade (Draft)
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
