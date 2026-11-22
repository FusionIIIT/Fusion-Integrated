import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Container,
  Divider,
  Group,
  Modal,
  Paper,
  Progress,
  Radio,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheckCircle,
  FaClock,
  FaExclamationCircle,
  FaListAlt,
  FaPlay,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAttemptDetail,
  useEligibleQuizzes,
  useSaveResponse,
  useStartAttempt,
  useSubmitAttempt,
} from "../api/hooks";
import type { OptionItem, Quiz } from "../api/types";

const STATUS_COLOR: Record<string, string> = {
  draft: "gray",
  scheduled: "blue",
  available: "green",
  closed: "orange",
  archived: "red",
};

export default function MyQuizzesPage() {
  const { data, isPending, error, refetch } = useEligibleQuizzes();
  const startAttempt = useStartAttempt();

  // Active attempt state
  const [activeAttemptId, setActiveAttemptId] = useState<number | null>(null);
  const [selectedQuiz, setSelectedQuiz] = useState<Quiz | null>(null);
  const [instructionsModalOpen, setInstructionsModalOpen] = useState(false);

  if (activeAttemptId) {
    return (
      <QuizTakingView
        attemptId={activeAttemptId}
        onFinished={() => {
          setActiveAttemptId(null);
          refetch();
        }}
      />
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Quizzes"
        subtitle="Available and upcoming quizzes for your enrolled courses"
      />

      {error ? (
        <ErrorState error={error} />
      ) : (
        <Card padding="lg" radius="md" withBorder>
          <DataTable<Quiz>
            rows={data?.results ?? []}
            loading={isPending}
            rowKey={(r) => r.id}
            empty={{
              icon: FaListAlt,
              title: "No Quizzes Available",
              description: "You have no pending quizzes or upcoming assessments right now.",
            }}
            columns={[
              {
                key: "title",
                header: "Quiz & Course",
                render: (r) => (
                  <Stack gap={2}>
                    <Text fw={600}>{r.title}</Text>
                    <Text size="xs" c="dimmed">
                      {r.course} · {r.question_count} Questions
                    </Text>
                  </Stack>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (r) => (
                  <Badge color={STATUS_COLOR[r.status] ?? "gray"} variant="light">
                    {r.status.toUpperCase()}
                  </Badge>
                ),
              },
              {
                key: "duration",
                header: "Duration",
                render: (r) => (
                  <Text size="sm">{r.duration_minutes} mins</Text>
                ),
              },
              {
                key: "marks",
                header: "Max Marks",
                render: (r) => (
                  <Text size="sm">{r.max_marks} marks</Text>
                ),
              },
              {
                key: "attempts",
                header: "Attempts",
                render: (r) => (
                  <Text size="sm">Max: {r.max_attempts}</Text>
                ),
              },
              {
                key: "actions",
                header: "Action",
                align: "right",
                render: (r) => {
                  const isAvailable = r.status === "available";
                  return (
                    <Button
                      size="xs"
                      variant={isAvailable ? "filled" : "light"}
                      color={isAvailable ? "blue" : "gray"}
                      disabled={!isAvailable}
                      leftSection={<FaPlay size={10} />}
                      onClick={() => {
                        setSelectedQuiz(r);
                        setInstructionsModalOpen(true);
                      }}
                    >
                      {isAvailable ? "Take Quiz" : "Upcoming"}
                    </Button>
                  );
                },
              },
            ]}
          />
        </Card>
      )}

      {/* Instructions Modal */}
      <Modal
        opened={instructionsModalOpen}
        onClose={() => setInstructionsModalOpen(false)}
        title={<Text fw={600} size="lg">Quiz Instructions</Text>}
        centered
        size="md"
      >
        {selectedQuiz && (
          <Stack gap="md">
            <Box>
              <Text fw={600} size="md">{selectedQuiz.title}</Text>
              <Text size="xs" c="dimmed">{selectedQuiz.course}</Text>
            </Box>

            <Paper p="sm" withBorder bg="gray.0">
              <SimpleGrid cols={2} spacing="xs">
                <Text size="sm"><strong>Duration:</strong> {selectedQuiz.duration_minutes} min</Text>
                <Text size="sm"><strong>Max Marks:</strong> {selectedQuiz.max_marks}</Text>
                <Text size="sm"><strong>Questions:</strong> {selectedQuiz.question_count}</Text>
                <Text size="sm"><strong>Max Attempts:</strong> {selectedQuiz.max_attempts}</Text>
              </SimpleGrid>
            </Paper>

            {selectedQuiz.instructions ? (
              <Box>
                <Text fw={500} size="sm" mb={4}>Instructions from Professor:</Text>
                <Text size="sm" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
                  {selectedQuiz.instructions}
                </Text>
              </Box>
            ) : null}

            <Alert icon={<FaExclamationCircle size={16} />} color="blue">
              Once you start, the timer will begin. Ensure a stable internet connection.
            </Alert>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setInstructionsModalOpen(false)}>
                Cancel
              </Button>
              <Button
                color="blue"
                leftSection={<FaPlay size={12} />}
                loading={startAttempt.isPending}
                onClick={() => {
                  startAttempt.mutate(selectedQuiz.id, {
                    onSuccess: (attempt) => {
                      setInstructionsModalOpen(false);
                      setActiveAttemptId(attempt.id);
                      notifications.show({
                        color: "green",
                        title: "Attempt Started",
                        message: "Best of luck with your assessment!",
                      });
                    },
                    onError: (e) => {
                      notifications.show({
                        color: "red",
                        title: "Cannot start attempt",
                        message: errorMessage(e),
                      });
                    },
                  });
                }}
              >
                Start Attempt Now
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}

// ---------------------------------------------------------------------------
// Quiz Taking View (in-progress assessment)
// ---------------------------------------------------------------------------

function QuizTakingView({
  attemptId,
  onFinished,
}: {
  attemptId: number;
  onFinished: () => void;
}) {
  const { data: attempt, isPending, error } = useAttemptDetail(attemptId, true);
  const saveResp = useSaveResponse();
  const submitAttempt = useSubmitAttempt();

  const [currentIndex, setCurrentIndex] = useState(0);
  const [localResponses, setLocalResponses] = useState<Record<number, unknown>>({});
  const [confirmSubmitOpen, setConfirmSubmitOpen] = useState(false);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  // Sync initial responses from server
  useEffect(() => {
    if (attempt?.responses) {
      const map: Record<number, unknown> = {};
      for (const r of attempt.responses) {
        if (r.response !== null && r.response !== undefined) {
          map[r.question] = r.response;
        }
      }
      setLocalResponses(map);
    }
  }, [attempt?.responses]);

  // Timer countdown
  useEffect(() => {
    if (attempt?.time_remaining_seconds !== undefined && attempt.time_remaining_seconds !== null) {
      setTimeLeft(attempt.time_remaining_seconds);
    }
  }, [attempt?.time_remaining_seconds]);

  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  // Auto-submit when time expires
  useEffect(() => {
    if (timeLeft === 0 && attempt?.status === "in_progress") {
      submitAttempt.mutate(attemptId, {
        onSuccess: () => {
          notifications.show({
            color: "orange",
            title: "Time Expired",
            message: "Your quiz attempt was automatically submitted.",
          });
          onFinished();
        },
      });
    }
  }, [timeLeft, attempt?.status, attemptId, submitAttempt, onFinished]);

  if (isPending) return <Container size="md" py="xl"><Text>Loading quiz...</Text></Container>;
  if (error || !attempt) return <Container size="md" py="xl"><ErrorState error={error} /></Container>;

  const questions = attempt.questions ?? [];
  const currentQ = questions[currentIndex];
  const totalQuestions = questions.length;

  const answeredCount = Object.keys(localResponses).length;
  const unansweredCount = Math.max(0, totalQuestions - answeredCount);

  function handleAnswerChange(val: unknown) {
    if (!currentQ) return;
    setLocalResponses((prev) => ({ ...prev, [currentQ.id]: val }));
    saveResp.mutate({
      attemptId,
      questionId: currentQ.id,
      response: val,
    });
  }

  function formatTime(secs: number | null) {
    if (secs === null) return "--:--";
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }

  return (
    <Container size="md" py="lg">
      <Card padding="md" withBorder radius="md" mb="md">
        <Group justify="space-between" align="center">
          <Box>
            <Title order={3}>{attempt.quiz_title}</Title>
            <Text size="xs" c="dimmed">
              Question {currentIndex + 1} of {totalQuestions} · Attempt #{attempt.attempt_number}
            </Text>
          </Box>
          <Group gap="xs">
            <Badge
              size="lg"
              color={timeLeft !== null && timeLeft < 300 ? "red" : "blue"}
              variant="filled"
              leftSection={<FaClock size={12} />}
            >
              Time Left: {formatTime(timeLeft)}
            </Badge>
            <Button
              color="green"
              size="xs"
              leftSection={<FaCheckCircle size={12} />}
              onClick={() => setConfirmSubmitOpen(true)}
            >
              Submit Quiz
            </Button>
          </Group>
        </Group>
        <Progress
          value={totalQuestions > 0 ? ((currentIndex + 1) / totalQuestions) * 100 : 0}
          mt="sm"
          size="xs"
        />
      </Card>

      {currentQ ? (
        <Card padding="lg" withBorder radius="md">
          <Stack gap="md">
            <Group justify="space-between" align="flex-start">
              <Text fw={600} size="md">
                Q{currentIndex + 1}. {currentQ.text}
              </Text>
              <Badge variant="outline" size="sm">
                {currentQ.marks} Marks
                {currentQ.negative_marks > 0 ? ` (-${currentQ.negative_marks})` : ""}
              </Badge>
            </Group>

            <Divider />

            {/* Answer Input depending on Question Type */}
            {currentQ.question_type === "mcq" && (
              <Radio.Group
                value={(localResponses[currentQ.id] as string) || ""}
                onChange={(val) => handleAnswerChange(val)}
              >
                <Stack gap="sm">
                  {(currentQ.options ?? []).map((opt: OptionItem) => (
                    <Paper key={opt.id} p="xs" withBorder radius="sm">
                      <Radio value={opt.id} label={opt.text} />
                    </Paper>
                  ))}
                </Stack>
              </Radio.Group>
            )}

            {currentQ.question_type === "msq" && (
              <Checkbox.Group
                value={(localResponses[currentQ.id] as string[]) || []}
                onChange={(val) => handleAnswerChange(val)}
              >
                <Stack gap="sm">
                  {(currentQ.options ?? []).map((opt: OptionItem) => (
                    <Paper key={opt.id} p="xs" withBorder radius="sm">
                      <Checkbox value={opt.id} label={opt.text} />
                    </Paper>
                  ))}
                </Stack>
              </Checkbox.Group>
            )}

            {currentQ.question_type === "tf" && (
              <Radio.Group
                value={(localResponses[currentQ.id] as string) || ""}
                onChange={(val) => handleAnswerChange(val)}
              >
                <Stack gap="sm">
                  <Paper p="xs" withBorder radius="sm">
                    <Radio value="true" label="True" />
                  </Paper>
                  <Paper p="xs" withBorder radius="sm">
                    <Radio value="false" label="False" />
                  </Paper>
                </Stack>
              </Radio.Group>
            )}

            {currentQ.question_type === "fitb" && (
              <TextInput
                placeholder="Type your answer here..."
                value={(localResponses[currentQ.id] as string) || ""}
                onChange={(e) => handleAnswerChange(e.currentTarget.value)}
              />
            )}

            {currentQ.question_type === "short" && (
              <Textarea
                placeholder="Write your explanation or solution here..."
                minRows={4}
                value={(localResponses[currentQ.id] as string) || ""}
                onChange={(e) => handleAnswerChange(e.currentTarget.value)}
              />
            )}

            <Divider mt="md" />

            {/* Navigation buttons */}
            <Group justify="space-between">
              <Button
                variant="default"
                disabled={currentIndex === 0 || !attempt.allow_back_navigation}
                onClick={() => setCurrentIndex((p) => Math.max(0, p - 1))}
              >
                Previous
              </Button>
              {currentIndex < totalQuestions - 1 ? (
                <Button
                  onClick={() =>
                    setCurrentIndex((p) => Math.min(totalQuestions - 1, p + 1))
                  }
                >
                  Next
                </Button>
              ) : (
                <Button
                  color="green"
                  onClick={() => setConfirmSubmitOpen(true)}
                >
                  Review & Submit
                </Button>
              )}
            </Group>
          </Stack>
        </Card>
      ) : (
        <Text c="dimmed">No questions found in this quiz.</Text>
      )}

      {/* Confirmation Modal */}
      <Modal
        opened={confirmSubmitOpen}
        onClose={() => setConfirmSubmitOpen(false)}
        title={<Text fw={600} size="md">Confirm Quiz Submission</Text>}
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            You have answered <strong>{answeredCount}</strong> out of{" "}
            <strong>{totalQuestions}</strong> questions.
          </Text>

          {unansweredCount > 0 && (
            <Alert color="yellow" icon={<FaExclamationCircle size={16} />}>
              You still have {unansweredCount} unanswered question(s). Once submitted,
              you cannot change your answers.
            </Alert>
          )}

          <Group justify="flex-end" mt="md">
            <Button
              variant="default"
              onClick={() => setConfirmSubmitOpen(false)}
            >
              Continue Quiz
            </Button>
            <Button
              color="green"
              loading={submitAttempt.isPending}
              onClick={() => {
                submitAttempt.mutate(attemptId, {
                  onSuccess: () => {
                    notifications.show({
                      color: "green",
                      title: "Quiz Submitted",
                      message: "Your responses have been recorded.",
                    });
                    setConfirmSubmitOpen(false);
                    onFinished();
                  },
                  onError: (e) => {
                    notifications.show({
                      color: "red",
                      title: "Submission failed",
                      message: errorMessage(e),
                    });
                  },
                });
              }}
            >
              Confirm & Submit
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
