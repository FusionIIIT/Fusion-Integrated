import { useState } from "react";
import {
  Badge,
  Box,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  Paper,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import { FaChartBar, FaEye } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyResultDetail, useMyResults } from "../api/hooks";
import type { AttemptResponse, QuizAttempt } from "../api/types";

export default function MyResultsPage() {
  const { data, isPending, error } = useMyResults();
  const [selectedAttemptId, setSelectedAttemptId] = useState<number | null>(null);

  return (
    <Container size="xl">
      <PageHeader
        title="My Quiz Results"
        subtitle="Review scores and feedback for your completed assessments"
      />

      {error ? (
        <ErrorState error={error} />
      ) : (
        <Card padding="lg" radius="md" withBorder>
          <DataTable<QuizAttempt>
            rows={data?.results ?? []}
            loading={isPending}
            rowKey={(r) => r.id}
            empty={{
              icon: FaChartBar,
              title: "No Results Released Yet",
              description: "Results will appear here once released by your professors.",
            }}
            columns={[
              {
                key: "quiz",
                header: "Quiz & Course",
                render: (r) => (
                  <Stack gap={2}>
                    <Text fw={600}>{r.quiz_title}</Text>
                    <Text size="xs" c="dimmed">
                      {r.quiz_course} · Attempt #{r.attempt_number}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "score",
                header: "Score",
                render: (r) => (
                  <Text fw={600}>
                    {r.score !== null ? r.score : "—"} marks
                  </Text>
                ),
              },
              {
                key: "percentage",
                header: "Percentage",
                render: (r) => (
                  <Text size="sm">
                    {r.percentage !== null ? `${r.percentage}%` : "—"}
                  </Text>
                ),
              },
              {
                key: "status",
                header: "Outcome",
                render: (r) => {
                  if (r.passed === true) {
                    return <Badge color="green" variant="light">PASSED</Badge>;
                  }
                  if (r.passed === false) {
                    return <Badge color="red" variant="light">FAILED</Badge>;
                  }
                  return <Badge color="blue" variant="light">EVALUATED</Badge>;
                },
              },
              {
                key: "submitted_at",
                header: "Submitted",
                render: (r) => (
                  <Text size="xs" c="dimmed">
                    {r.submitted_at
                      ? new Date(r.submitted_at).toLocaleDateString()
                      : "—"}
                  </Text>
                ),
              },
              {
                key: "actions",
                header: "Details",
                align: "right",
                render: (r) => (
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<FaEye size={12} />}
                    onClick={() => setSelectedAttemptId(r.id)}
                  >
                    View Breakdown
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      )}

      {selectedAttemptId && (
        <ResultDetailModal
          attemptId={selectedAttemptId}
          onClose={() => setSelectedAttemptId(null)}
        />
      )}
    </Container>
  );
}

function ResultDetailModal({
  attemptId,
  onClose,
}: {
  attemptId: number;
  onClose: () => void;
}) {
  const { data: attempt, isPending, error } = useMyResultDetail(attemptId);

  return (
    <Modal
      opened={Boolean(attemptId)}
      onClose={onClose}
      title={<Text fw={600} size="lg">Result Breakdown</Text>}
      size="lg"
      centered
    >
      {isPending ? (
        <Text>Loading details...</Text>
      ) : error || !attempt ? (
        <ErrorState error={error} />
      ) : (
        <Stack gap="md">
          <Paper p="md" withBorder bg="gray.0" radius="sm">
            <SimpleGrid cols={3} spacing="xs">
              <Box>
                <Text size="xs" c="dimmed">Total Score</Text>
                <Text fw={700} size="md">{attempt.score ?? 0} marks</Text>
              </Box>
              <Box>
                <Text size="xs" c="dimmed">Percentage</Text>
                <Text fw={700} size="md">{attempt.percentage ?? 0}%</Text>
              </Box>
              <Box>
                <Text size="xs" c="dimmed">Result</Text>
                {attempt.passed === true ? (
                  <Badge color="green">PASSED</Badge>
                ) : attempt.passed === false ? (
                  <Badge color="red">FAILED</Badge>
                ) : (
                  <Badge color="blue">COMPLETED</Badge>
                )}
              </Box>
            </SimpleGrid>
          </Paper>

          <Divider label="Question Responses" labelPosition="center" />

          <Stack gap="sm">
            {(attempt.responses ?? []).map((resp: AttemptResponse, idx: number) => (
              <Paper key={resp.id} p="sm" withBorder radius="sm">
                <Group justify="space-between" align="flex-start" mb="xs">
                  <Text fw={600} size="sm">
                    Q{idx + 1}. {resp.question_text}
                  </Text>
                  <Badge
                    color={
                      resp.is_correct === true
                        ? "green"
                        : resp.is_correct === false
                        ? "red"
                        : "blue"
                    }
                    variant="light"
                    size="sm"
                  >
                    {resp.marks_obtained !== null ? `${resp.marks_obtained} / ` : ""}
                    {resp.marks} marks
                  </Badge>
                </Group>

                <Box mb="xs">
                  <Text size="xs" c="dimmed">Your Answer:</Text>
                  <Text size="sm">
                    {resp.response !== null && resp.response !== undefined
                      ? typeof resp.response === "object"
                        ? JSON.stringify(resp.response)
                        : String(resp.response)
                      : "(No answer provided)"}
                  </Text>
                </Box>

                {resp.professor_feedback ? (
                  <Paper p="xs" bg="blue.0" radius="xs">
                    <Text size="xs" fw={500} c="blue.8">
                      Feedback: {resp.professor_feedback}
                    </Text>
                  </Paper>
                ) : null}
              </Paper>
            ))}
          </Stack>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Close
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
