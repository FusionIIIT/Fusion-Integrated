import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useCourse, useGrades } from "../api/hooks";

export const ReleasedGradesPage: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const cId = Number(courseId);

  const { data: course, isLoading: isCourseLoading } = useCourse(cId);
  const { data: grades = [], isLoading: isGradesLoading } = useGrades();

  // Filter only released grades
  const releasedGrades = grades.filter(
    (g) => !g.is_draft && Boolean(g.released_at)
  );

  const isLoading = isCourseLoading || isGradesLoading;

  return (
    <Stack gap="lg" p="md">
      <Group justify="space-between">
        <div>
          <Title order={2}>Academic Grade Report</Title>
          <Text c="dimmed">
            {isCourseLoading ? "Loading course..." : `${course?.code} — ${course?.name}`}
          </Text>
        </div>
        <Button variant="default" onClick={() => navigate(`/courses/${cId}`)}>
          Back to Course
        </Button>
      </Group>

      <Alert color="blue" title="Grading Policy Notice (BW-LMS-05 / ISS-LMS-006)">
        Only official grades released by Course Instructors are visible in this report.
        Preliminary evaluations and draft reviews remain confidential until released.
      </Alert>

      {isLoading ? (
        <Group justify="center" p="xl">
          <Loader size="md" />
          <Text c="dimmed">Loading grade records...</Text>
        </Group>
      ) : releasedGrades.length === 0 ? (
        <Paper withBorder p="xl" style={{ textAlign: "center" }}>
          <Text c="dimmed">No released grades are currently available for this course.</Text>
        </Paper>
      ) : (
        <Card withBorder padding="none">
          <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Submission</Table.Th>
                <Table.Th>Score Awarded</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Feedback</Table.Th>
                <Table.Th>Released On</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {releasedGrades.map((grade) => {
                return (
                  <Table.Tr key={grade.id}>
                    <Table.Td>
                      <Text fw={600}>
                        Submission #{grade.submission}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={700} c="blue">
                        {grade.points_awarded} pts
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color="green" variant="filled">
                        Released
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{grade.feedback_text || "No feedback provided."}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" c="dimmed">
                        {grade.released_at
                          ? new Date(grade.released_at).toLocaleString()
                          : new Date(grade.updated_at).toLocaleString()}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
};

export default ReleasedGradesPage;
