import { useNavigate } from "react-router-dom";
import {
  Badge,
  Card,
  Container,
  Grid,
  Group,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { FaAward, FaChartBar, FaCheckCircle, FaGraduationCap } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyGrades } from "../api/hooks";

export default function GradesPage() {
  const navigate = useNavigate();
  const { data: mySubmissions, isPending, error } = useMyGrades();

  if (error) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const list = mySubmissions ?? [];
  const gradedList = list.filter((s) => s.grade && s.grade.status === "released");

  const totalPossible = gradedList.reduce(
    (acc, s) => acc + Number(s.assignment_points_possible || 0),
    0,
  );
  const totalEarned = gradedList.reduce(
    (acc, s) => acc + Number(s.grade?.points_awarded || 0),
    0,
  );
  const overallPercentage =
    totalPossible > 0 ? ((totalEarned / totalPossible) * 100).toFixed(1) : "—";

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="My Grades &amp; Academic Progress"
        subtitle="Official released evaluations, score summaries, and feedback from instructors"
      />

      {/* Summary Scorecard */}
      <Grid mb="lg">
        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed">
                  Evaluated Assignments
                </Text>
                <Title order={3}>{gradedList.length}</Title>
              </div>
              <ThemeIcon size={38} radius="xl" color="indigo" variant="light">
                <FaCheckCircle size={18} />
              </ThemeIcon>
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed">
                  Total Points Awarded
                </Text>
                <Title order={3}>
                  {totalEarned} / {totalPossible}
                </Title>
              </div>
              <ThemeIcon size={38} radius="xl" color="teal" variant="light">
                <FaAward size={18} />
              </ThemeIcon>
            </Group>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, sm: 4 }}>
          <Card withBorder padding="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed">
                  Overall Average
                </Text>
                <Title order={3}>{overallPercentage}%</Title>
              </div>
              <ThemeIcon size={38} radius="xl" color="blue" variant="light">
                <FaChartBar size={18} />
              </ThemeIcon>
            </Group>
          </Card>
        </Grid.Col>
      </Grid>

      {isPending && <Text c="dimmed">Loading gradebook...</Text>}

      {!isPending && gradedList.length === 0 && (
        <Card padding="xl" withBorder style={{ textAlign: "center" }}>
          <Stack align="center" gap="xs">
            <ThemeIcon size={46} radius="xl" color="gray" variant="light">
              <FaGraduationCap size={22} />
            </ThemeIcon>
            <Text fw={600} size="md">
              No released grades available
            </Text>
            <Text c="dimmed" size="xs">
              Grades will appear here once your instructors publish the official evaluations (BR-LMS-016).
            </Text>
          </Stack>
        </Card>
      )}

      {gradedList.length > 0 && (
        <Card withBorder padding="md" radius="md">
          <Table highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Assignment</Table.Th>
                <Table.Th>Submitted At</Table.Th>
                <Table.Th>Submission Status</Table.Th>
                <Table.Th>Score Awarded</Table.Th>
                <Table.Th>Percentage</Table.Th>
                <Table.Th>Instructor Feedback</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {gradedList.map((s) => {
                const pts = Number(s.grade?.points_awarded || 0);
                const maxPts = Number(s.assignment_points_possible || 0);
                const pct = maxPts > 0 ? ((pts / maxPts) * 100).toFixed(1) : "—";

                return (
                  <Table.Tr
                    key={s.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => navigate(`/lms/assignments?assignmentId=${s.assignment}`)}
                  >
                    <Table.Td>
                      <strong>{s.assignment_title}</strong>
                    </Table.Td>
                    <Table.Td>{new Date(s.submitted_at).toLocaleDateString()}</Table.Td>
                    <Table.Td>
                      <Badge color={s.status === "late" ? "orange" : "teal"} size="xs">
                        {s.status.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={700}>
                        {pts} / {maxPts}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge
                        color={Number(pct) >= 75 ? "green" : Number(pct) >= 50 ? "blue" : "red"}
                        variant="light"
                        size="sm"
                      >
                        {pct}%
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" lineClamp={2}>
                        {s.grade?.feedback || "No feedback"}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Container>
  );
}
