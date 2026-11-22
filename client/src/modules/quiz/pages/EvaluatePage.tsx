import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheck,
  FaCheckCircle,
  FaEdit,
  FaPaperPlane,
  FaRobot,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAttemptForEvaluation,
  useEvaluateAttempt,
  useQuizSubmissions,
  useQuizzes,
  useReleaseAllResults,
  useReleaseAttemptResult,
} from "../api/hooks";
import type { QuizAttempt } from "../api/types";

export default function EvaluatePage() {
  const { data: quizzesData, isPending: quizzesLoading, error: quizzesError } = useQuizzes();
  const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);
  const [evaluatingAttemptId, setEvaluatingAttemptId] = useState<number | null>(null);

  const quizIdNumber = selectedQuizId ? Number(selectedQuizId) : undefined;
  const {
    data: submissionsData,
    isPending: submissionsLoading,
    error: submissionsError,
  } = useQuizSubmissions(quizIdNumber);

  const releaseAll = useReleaseAllResults();
  const releaseAttempt = useReleaseAttemptResult(quizIdNumber);

  // Auto-select first quiz if none selected
  useEffect(() => {
    if (!selectedQuizId && quizzesData?.results && quizzesData.results.length > 0 && quizzesData.results[0]) {
      setSelectedQuizId(String(quizzesData.results[0].id));
    }
  }, [quizzesData, selectedQuizId]);

  const quizOptions = (quizzesData?.results ?? []).map((q) => ({
    value: String(q.id),
    label: `${q.title} (${q.course})`,
  }));

  const handleReleaseAll = async () => {
    if (!quizIdNumber) return;
    if (
      !window.confirm(
        "Are you sure you want to release results for all evaluated submissions in this quiz?"
      )
    ) {
      return;
    }
    try {
      const res = await releaseAll.mutateAsync(quizIdNumber);
      notifications.show({
        color: "green",
        message: `Successfully released results for ${res.released} student submission(s)`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Release failed",
        message: errorMessage(err),
      });
    }
  };

  const handleReleaseSingle = async (attemptId: number) => {
    try {
      await releaseAttempt.mutateAsync(attemptId);
      notifications.show({
        color: "green",
        message: "Attempt results released to student",
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Release failed",
        message: errorMessage(err),
      });
    }
  };

  if (quizzesError) {
    return (
      <Container size="xl">
        <ErrorState error={quizzesError} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Evaluate Quizzes"
        subtitle="Review student submissions, evaluate subjective responses with AI assistance, and release grades"
        action={
          quizIdNumber && (
            <Button
              color="green"
              leftSection={<FaPaperPlane size={12} />}
              loading={releaseAll.isPending}
              onClick={handleReleaseAll}
            >
              Release All Evaluated
            </Button>
          )
        }
      />

      <Card padding="md" mb="lg" radius="md" withBorder>
        <Group justify="space-between" align="flex-end">
          <Select
            label="Select Quiz"
            placeholder="Choose an assessment to evaluate"
            data={quizOptions}
            value={selectedQuizId}
            onChange={setSelectedQuizId}
            disabled={quizzesLoading}
            style={{ width: 380 }}
          />
          {selectedQuizId && (
            <Text size="sm" c="dimmed">
              Total Submissions: {submissionsData?.results.length ?? 0}
            </Text>
          )}
        </Group>
      </Card>

      {submissionsError ? (
        <ErrorState error={submissionsError} />
      ) : (
        <Card padding="lg" radius="md" withBorder>
          <DataTable<QuizAttempt>
            rows={submissionsData?.results ?? []}
            loading={submissionsLoading}
            rowKey={(r) => r.id}
            empty={{
              icon: FaCheckCircle,
              title: "No Submissions Found",
              description: selectedQuizId
                ? "No student submissions yet for this quiz."
                : "Select a quiz above to view student submissions.",
            }}
            columns={[
              {
                key: "student",
                header: "Student & Attempt",
                render: (r) => (
                  <Stack gap={2}>
                    <Text fw={600}>Student #{r.user_id}</Text>
                    <Text size="xs" c="dimmed">
                      Attempt #{r.attempt_number} · ID #{r.id}
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (r) => <StatusBadge status={r.status} />,
              },
              {
                key: "score",
                header: "Score",
                render: (r) => (
                  <Text fw={600}>
                    {r.score !== null ? `${r.score} marks` : "Pending evaluation"}
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
                key: "passed",
                header: "Result",
                render: (r) =>
                  r.passed === null ? (
                    <Badge color="gray" variant="light" size="sm">
                      Pending
                    </Badge>
                  ) : r.passed ? (
                    <Badge color="green" variant="light" size="sm">
                      Passed
                    </Badge>
                  ) : (
                    <Badge color="red" variant="light" size="sm">
                      Failed
                    </Badge>
                  ),
              },
              {
                key: "violations",
                header: "Tab Violations",
                render: (r) =>
                  r.tab_violations > 0 ? (
                    <Badge color="red" variant="subtle" size="sm">
                      {r.tab_violations} warnings
                    </Badge>
                  ) : (
                    <Text size="xs" c="dimmed">
                      None
                    </Text>
                  ),
              },
              {
                key: "submitted_at",
                header: "Submitted At",
                render: (r) => (
                  <Text size="xs">
                    {r.submitted_at
                      ? new Date(r.submitted_at).toLocaleString()
                      : "In progress"}
                  </Text>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                align: "right",
                render: (r) => (
                  <Group gap="xs" justify="flex-end">
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<FaEdit size={12} />}
                      onClick={() => setEvaluatingAttemptId(r.id)}
                    >
                      Evaluate
                    </Button>
                    {(r.status === "evaluated" || r.status === "partially_evaluated") && (
                      <Button
                        size="xs"
                        color="green"
                        variant="subtle"
                        leftSection={<FaCheck size={12} />}
                        loading={releaseAttempt.isPending}
                        onClick={() => handleReleaseSingle(r.id)}
                      >
                        Release
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
          />
        </Card>
      )}

      {/* Evaluation Modal */}
      {evaluatingAttemptId && (
        <EvaluationModal
          attemptId={evaluatingAttemptId}
          quizId={quizIdNumber}
          onClose={() => setEvaluatingAttemptId(null)}
        />
      )}
    </Container>
  );
}

// ---------------------------------------------------------------------------
// Attempt Evaluation Modal Component
// ---------------------------------------------------------------------------

function EvaluationModal({
  attemptId,
  quizId,
  onClose,
}: {
  attemptId: number;
  quizId?: number;
  onClose: () => void;
}) {
  const { data: attempt, isPending, error } = useAttemptForEvaluation(attemptId);
  const evaluate = useEvaluateAttempt(quizId);
  const release = useReleaseAttemptResult(quizId);

  // Local state for professor grades and feedback for each response
  const [grades, setGrades] = useState<
    Record<number, { marks: number | null; feedback: string }>
  >({});

  // Initialize grades from attempt responses
  useEffect(() => {
    if (attempt?.responses) {
      const initial: Record<number, { marks: number | null; feedback: string }> = {};
      for (const r of attempt.responses) {
        initial[r.id] = {
          marks:
            r.marks_obtained !== null
              ? Number(r.marks_obtained)
              : r.ai_suggested_marks !== null
              ? Number(r.ai_suggested_marks)
              : null,
          feedback: r.professor_feedback || "",
        };
      }
      setGrades(initial);
    }
  }, [attempt]);

  const handleSaveEvaluation = async (autoRelease = false) => {
    if (!attempt) return;
    const payload = attempt.responses.map((r) => ({
      response_id: r.id,
      marks_obtained: grades[r.id]?.marks ?? null,
      professor_feedback: grades[r.id]?.feedback ?? "",
      ai_suggested_marks: r.ai_suggested_marks,
    }));

    try {
      await evaluate.mutateAsync({
        attemptId: attempt.id,
        responses: payload,
      });

      if (autoRelease) {
        await release.mutateAsync(attempt.id);
        notifications.show({
          color: "green",
          message: "Evaluation saved and results released",
        });
      } else {
        notifications.show({
          color: "green",
          message: "Evaluation saved successfully",
        });
      }
      onClose();
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Failed to save evaluation",
        message: errorMessage(err),
      });
    }
  };

  return (
    <Modal
      opened
      onClose={onClose}
      title={
        <Text fw={700}>
          Evaluate Attempt #{attemptId} (Student #{attempt?.user_id})
        </Text>
      }
      size="xl"
    >
      {isPending ? (
        <Text size="sm" c="dimmed">
          Loading submission details...
        </Text>
      ) : error ? (
        <ErrorState error={error} />
      ) : !attempt ? null : (
        <Stack gap="md">
          <SimpleGrid cols={4} spacing="xs">
            <Paper p="xs" withBorder>
              <Text size="xs" c="dimmed">
                Status
              </Text>
              <StatusBadge status={attempt.status} />
            </Paper>
            <Paper p="xs" withBorder>
              <Text size="xs" c="dimmed">
                Score
              </Text>
              <Text fw={600} size="sm">
                {attempt.score !== null ? `${attempt.score} marks` : "Pending"}
              </Text>
            </Paper>
            <Paper p="xs" withBorder>
              <Text size="xs" c="dimmed">
                Time Taken
              </Text>
              <Text size="sm">
                {attempt.time_taken_seconds
                  ? `${Math.round(attempt.time_taken_seconds / 60)} mins`
                  : "—"}
              </Text>
            </Paper>
            <Paper p="xs" withBorder>
              <Text size="xs" c="dimmed">
                Tab Violations
              </Text>
              <Text size="sm" c={attempt.tab_violations > 0 ? "red" : "dimmed"}>
                {attempt.tab_violations}
              </Text>
            </Paper>
          </SimpleGrid>

          <Divider />

          <Stack gap="md">
            {attempt.responses.map((resp, idx) => (
              <Card key={resp.id} withBorder padding="md" radius="md">
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <Badge variant="filled" size="sm">
                      Question {idx + 1}
                    </Badge>
                    <Badge variant="light" size="sm">
                      {resp.question_type.toUpperCase()}
                    </Badge>
                    <Badge color="blue" variant="subtle" size="sm">
                      Max: {resp.marks} marks
                    </Badge>
                  </Group>
                  {resp.is_correct !== null && (
                    <Badge
                      color={resp.is_correct ? "green" : "red"}
                      variant="filled"
                      size="sm"
                    >
                      {resp.is_correct ? "Auto-Graded: Correct" : "Auto-Graded: Incorrect"}
                    </Badge>
                  )}
                </Group>

                <Text fw={600} size="sm" mb="xs">
                  {resp.question_text}
                </Text>

                <Paper p="sm" withBorder bg="var(--mantine-color-gray-0)" mb="xs">
                  <Text size="xs" c="dimmed" mb={2}>
                    Student's Submitted Response:
                  </Text>
                  <Text size="sm" fw={500}>
                    {resp.response === null || resp.response === undefined
                      ? "(No response submitted)"
                      : typeof resp.response === "object"
                      ? JSON.stringify(resp.response)
                      : String(resp.response)}
                  </Text>
                </Paper>

                {/* AI Evaluation Assistance for Subjective Questions */}
                {resp.question_type === "short" && (
                  <Stack gap="xs" mb="xs">
                    {resp.ai_suggested_marks !== null && (
                      <Alert
                        icon={<FaRobot size={16} />}
                        title="AI Suggested Evaluation"
                        color="indigo"
                        variant="light"
                      >
                        <Group justify="space-between" mb={4}>
                          <Text size="xs" fw={700}>
                            Suggested Marks: {resp.ai_suggested_marks} / {resp.marks}
                          </Text>
                        </Group>
                        {resp.ai_reasoning && (
                          <Text size="xs">{resp.ai_reasoning}</Text>
                        )}
                      </Alert>
                    )}
                  </Stack>
                )}

                {/* Professor Evaluation Controls */}
                <Group grow align="flex-start" mt="xs">
                  <NumberInput
                    label="Awarded Marks"
                    min={0}
                    max={Number(resp.marks)}
                    step={0.5}
                    value={grades[resp.id]?.marks ?? ""}
                    onChange={(v) =>
                      setGrades((prev) => {
                        const current = prev[resp.id] ?? { marks: null, feedback: "" };
                        return {
                          ...prev,
                          [resp.id]: {
                            ...current,
                            marks: v === "" ? null : Number(v),
                          },
                        };
                      })
                    }
                  />
                  <Textarea
                    label="Professor Feedback"
                    placeholder="Feedback for student..."
                    minRows={1}
                    value={grades[resp.id]?.feedback ?? ""}
                    onChange={(e) =>
                      setGrades((prev) => {
                        const current = prev[resp.id] ?? { marks: null, feedback: "" };
                        return {
                          ...prev,
                          [resp.id]: {
                            ...current,
                            feedback: e.currentTarget.value,
                          },
                        };
                      })
                    }
                  />
                </Group>
              </Card>
            ))}
          </Stack>

          <Group justify="flex-end" mt="lg">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="outline"
              loading={evaluate.isPending}
              onClick={() => handleSaveEvaluation(false)}
            >
              Save Evaluation
            </Button>
            <Button
              color="green"
              loading={evaluate.isPending || release.isPending}
              onClick={() => handleSaveEvaluation(true)}
            >
              Save & Release Results
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
