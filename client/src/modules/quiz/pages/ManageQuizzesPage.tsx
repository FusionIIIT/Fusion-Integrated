import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Modal,
  NumberInput,
  Paper,
  Radio,
  Checkbox,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaArchive,
  FaCheck,
  FaClipboardList,
  FaEdit,
  FaPlus,
  FaTimesCircle,
  FaTrash,
  FaUpload,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { Field, FormRow, FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddBankQuestionToQuiz,
  useAddQuestion,
  useArchiveQuiz,
  useCloseQuiz,
  useCreateQuiz,
  useDeleteQuestion,
  useDeleteQuiz,
  usePublishQuiz,
  useQuestionBank,
  useQuizQuestions,
  useQuizzes,
  useUpdateQuiz,
} from "../api/hooks";
import type { OptionItem, Question, QuestionType, Quiz } from "../api/types";

export default function ManageQuizzesPage() {
  const { data, isPending, error } = useQuizzes();
  const createQuiz = useCreateQuiz();
  const publishQuiz = usePublishQuiz();
  const closeQuiz = useCloseQuiz();
  const archiveQuiz = useArchiveQuiz();
  const deleteQuiz = useDeleteQuiz();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [managingQuiz, setManagingQuiz] = useState<Quiz | null>(null);

  // New Quiz form state
  const [title, setTitle] = useState("");
  const [course, setCourse] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [durationMinutes, setDurationMinutes] = useState<number | string>(30);
  const [maxMarks, setMaxMarks] = useState<number | string>(50);
  const [passingMarks, setPassingMarks] = useState<number | string>("");
  const [maxAttempts, setMaxAttempts] = useState<number | string>(1);
  const [startAt, setStartAt] = useState("");
  const [closeAt, setCloseAt] = useState("");
  const [allowBackNav, setAllowBackNav] = useState(true);
  const [oneQuestionAtTime, setOneQuestionAtTime] = useState(false);
  const [randomizeQuestions, setRandomizeQuestions] = useState(false);
  const [randomizeOptions, setRandomizeOptions] = useState(false);
  const [allowUnanswered, setAllowUnanswered] = useState(true);
  const [tabBlock, setTabBlock] = useState(false);
  const [negativeMarking, setNegativeMarking] = useState(false);
  const [resultVisibility, setResultVisibility] = useState<string | null>("after_release");

  const resetCreateForm = () => {
    setTitle("");
    setCourse("");
    setDescription("");
    setInstructions("");
    setDurationMinutes(30);
    setMaxMarks(50);
    setPassingMarks("");
    setMaxAttempts(1);
    setStartAt("");
    setCloseAt("");
    setAllowBackNav(true);
    setOneQuestionAtTime(false);
    setRandomizeQuestions(false);
    setRandomizeOptions(false);
    setAllowUnanswered(true);
    setTabBlock(false);
    setNegativeMarking(false);
    setResultVisibility("after_release");
  };

  const handleCreateQuiz = async () => {
    if (!title.trim() || !course.trim()) {
      notifications.show({
        color: "red",
        message: "Title and Course are required",
      });
      return;
    }
    try {
      await createQuiz.mutateAsync({
        title,
        course,
        description,
        instructions,
        duration_minutes: Number(durationMinutes) || 30,
        max_marks: Number(maxMarks) || 50,
        passing_marks: passingMarks ? Number(passingMarks) : null,
        max_attempts: Number(maxAttempts) || 1,
        start_at: startAt ? new Date(startAt).toISOString() : null,
        close_at: closeAt ? new Date(closeAt).toISOString() : null,
        allow_back_navigation: allowBackNav,
        one_question_at_a_time: oneQuestionAtTime,
        randomize_questions: randomizeQuestions,
        randomize_options: randomizeOptions,
        allow_unanswered: allowUnanswered,
        tab_block: tabBlock,
        negative_marking: negativeMarking,
        result_visibility: (resultVisibility as Quiz["result_visibility"]) || "after_release",
      });
      notifications.show({
        color: "green",
        message: "Quiz created successfully",
      });
      setCreateModalOpen(false);
      resetCreateForm();
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Creation failed",
        message: errorMessage(err),
      });
    }
  };

  const handlePublish = async (quiz: Quiz) => {
    try {
      await publishQuiz.mutateAsync(quiz.id);
      notifications.show({
        color: "green",
        message: `Quiz "${quiz.title}" published`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Publish failed",
        message: errorMessage(err),
      });
    }
  };

  const handleClose = async (quiz: Quiz) => {
    try {
      await closeQuiz.mutateAsync(quiz.id);
      notifications.show({
        color: "orange",
        message: `Quiz "${quiz.title}" closed`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Close failed",
        message: errorMessage(err),
      });
    }
  };

  const handleArchive = async (quiz: Quiz) => {
    try {
      await archiveQuiz.mutateAsync(quiz.id);
      notifications.show({
        color: "gray",
        message: `Quiz "${quiz.title}" archived`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Archive failed",
        message: errorMessage(err),
      });
    }
  };

  const handleDelete = async (quiz: Quiz) => {
    if (!window.confirm(`Are you sure you want to delete "${quiz.title}"?`)) return;
    try {
      await deleteQuiz.mutateAsync(quiz.id);
      notifications.show({
        color: "green",
        message: `Quiz "${quiz.title}" deleted`,
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Delete failed",
        message: errorMessage(err),
      });
    }
  };

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Manage Quizzes"
        subtitle="Create, configure, and schedule quizzes for your courses"
        action={
          <Button
            leftSection={<FaPlus size={12} />}
            onClick={() => setCreateModalOpen(true)}
          >
            Create Quiz
          </Button>
        }
      />

      <Card padding="lg" radius="md" withBorder>
        <DataTable<Quiz>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{
            icon: FaClipboardList,
            title: "No Quizzes Created",
            description: "Click 'Create Quiz' to design and schedule your first assessment.",
          }}
          columns={[
            {
              key: "title",
              header: "Quiz & Course",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={600}>{r.title}</Text>
                  <Text size="xs" c="dimmed">
                    {r.course} · ID #{r.id}
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
              key: "marks",
              header: "Questions & Marks",
              render: (r) => (
                <Text size="sm">
                  {r.question_count} Qs · {r.max_marks} marks
                </Text>
              ),
            },
            {
              key: "timing",
              header: "Duration & Attempts",
              render: (r) => (
                <Text size="sm">
                  {r.duration_minutes}m · max {r.max_attempts}
                </Text>
              ),
            },
            {
              key: "window",
              header: "Schedule Window",
              render: (r) => (
                <Stack gap={1}>
                  <Text size="xs">
                    Start: {r.start_at ? new Date(r.start_at).toLocaleString() : "Immediate"}
                  </Text>
                  <Text size="xs" c="dimmed">
                    End: {r.close_at ? new Date(r.close_at).toLocaleString() : "No close date"}
                  </Text>
                </Stack>
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
                    onClick={() => setManagingQuiz(r)}
                  >
                    Manage
                  </Button>
                  {(r.status === "draft" || r.status === "scheduled") && (
                    <Button
                      size="xs"
                      color="green"
                      variant="subtle"
                      leftSection={<FaCheck size={12} />}
                      loading={publishQuiz.isPending}
                      onClick={() => handlePublish(r)}
                    >
                      Publish
                    </Button>
                  )}
                  {r.status === "available" && (
                    <Button
                      size="xs"
                      color="orange"
                      variant="subtle"
                      leftSection={<FaTimesCircle size={12} />}
                      loading={closeQuiz.isPending}
                      onClick={() => handleClose(r)}
                    >
                      Close
                    </Button>
                  )}
                  {r.status === "closed" && (
                    <Button
                      size="xs"
                      color="gray"
                      variant="subtle"
                      leftSection={<FaArchive size={12} />}
                      loading={archiveQuiz.isPending}
                      onClick={() => handleArchive(r)}
                    >
                      Archive
                    </Button>
                  )}
                  {r.status === "draft" && (
                    <ActionIcon
                      size="sm"
                      color="red"
                      variant="subtle"
                      loading={deleteQuiz.isPending}
                      onClick={() => handleDelete(r)}
                    >
                      <FaTrash size={12} />
                    </ActionIcon>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* Create Quiz Modal */}
      <Modal
        opened={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title={<Text fw={700}>Create New Quiz</Text>}
        size="lg"
      >
        <Stack gap="md">
          <FormSection title="General Information" first>
            <FormRow>
              <Field span={7}>
                <TextInput
                  label="Quiz Title"
                  required
                  placeholder="e.g. CS201 Midterm Exam"
                  value={title}
                  onChange={(e) => setTitle(e.currentTarget.value)}
                />
              </Field>
              <Field span={5}>
                <TextInput
                  label="Course Code / Name"
                  required
                  placeholder="e.g. CS201"
                  value={course}
                  onChange={(e) => setCourse(e.currentTarget.value)}
                />
              </Field>
            </FormRow>
            <FormRow>
              <Field span={12}>
                <Textarea
                  label="Description"
                  placeholder="Brief synopsis of topics covered"
                  minRows={2}
                  value={description}
                  onChange={(e) => setDescription(e.currentTarget.value)}
                />
              </Field>
            </FormRow>
            <FormRow>
              <Field span={12}>
                <Textarea
                  label="Instructions for Students"
                  placeholder="Rules, calculator policy, negative marking details..."
                  minRows={2}
                  value={instructions}
                  onChange={(e) => setInstructions(e.currentTarget.value)}
                />
              </Field>
            </FormRow>
          </FormSection>

          <FormSection title="Marks & Duration">
            <FormRow>
              <Field span={6}>
                <NumberInput
                  label="Duration (Minutes)"
                  required
                  min={1}
                  value={durationMinutes}
                  onChange={(v) => setDurationMinutes(v)}
                />
              </Field>
              <Field span={6}>
                <NumberInput
                  label="Max Marks"
                  required
                  min={0}
                  value={maxMarks}
                  onChange={(v) => setMaxMarks(v)}
                />
              </Field>
            </FormRow>
            <FormRow>
              <Field span={6}>
                <NumberInput
                  label="Passing Marks (Optional)"
                  min={0}
                  value={passingMarks}
                  onChange={(v) => setPassingMarks(v)}
                />
              </Field>
              <Field span={6}>
                <NumberInput
                  label="Max Attempts"
                  min={1}
                  value={maxAttempts}
                  onChange={(v) => setMaxAttempts(v)}
                />
              </Field>
            </FormRow>
            <FormRow>
              <Field span={6}>
                <TextInput
                  label="Start Window (YYYY-MM-DDTHH:MM)"
                  placeholder="2026-11-20T10:00"
                  value={startAt}
                  onChange={(e) => setStartAt(e.currentTarget.value)}
                />
              </Field>
              <Field span={6}>
                <TextInput
                  label="Close Window (YYYY-MM-DDTHH:MM)"
                  placeholder="2026-11-20T12:00"
                  value={closeAt}
                  onChange={(e) => setCloseAt(e.currentTarget.value)}
                />
              </Field>
            </FormRow>
          </FormSection>

          <FormSection title="Configuration & Proctoring">
            <SimpleGrid cols={2} spacing="sm">
              <Switch
                label="Allow Back Navigation"
                checked={allowBackNav}
                onChange={(e) => setAllowBackNav(e.currentTarget.checked)}
              />
              <Switch
                label="One Question at a Time"
                checked={oneQuestionAtTime}
                onChange={(e) => setOneQuestionAtTime(e.currentTarget.checked)}
              />
              <Switch
                label="Randomize Questions"
                checked={randomizeQuestions}
                onChange={(e) => setRandomizeQuestions(e.currentTarget.checked)}
              />
              <Switch
                label="Randomize Options"
                checked={randomizeOptions}
                onChange={(e) => setRandomizeOptions(e.currentTarget.checked)}
              />
              <Switch
                label="Allow Unanswered"
                checked={allowUnanswered}
                onChange={(e) => setAllowUnanswered(e.currentTarget.checked)}
              />
              <Switch
                label="Tab Proctoring (Block Tab Switching)"
                checked={tabBlock}
                onChange={(e) => setTabBlock(e.currentTarget.checked)}
              />
              <Switch
                label="Negative Marking"
                checked={negativeMarking}
                onChange={(e) => setNegativeMarking(e.currentTarget.checked)}
              />
              <Select
                label="Result Visibility"
                data={[
                  { value: "after_release", label: "After Professor Release" },
                  { value: "immediate", label: "Immediate on Submit" },
                  { value: "never", label: "Never" },
                ]}
                value={resultVisibility}
                onChange={setResultVisibility}
              />
            </SimpleGrid>
          </FormSection>

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={createQuiz.isPending} onClick={handleCreateQuiz}>
              Create Quiz
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Manage Quiz Modal (Questions & Settings) */}
      {managingQuiz && (
        <QuizManagementModal
          quiz={managingQuiz}
          onClose={() => setManagingQuiz(null)}
        />
      )}
    </Container>
  );
}

// ---------------------------------------------------------------------------
// Quiz Management Sub-component: Edit Settings, Question Bank, and Questions
// ---------------------------------------------------------------------------

function QuizManagementModal({
  quiz,
  onClose,
}: {
  quiz: Quiz;
  onClose: () => void;
}) {
  const updateQuiz = useUpdateQuiz();
  const { data: questionsData, isPending: questionsLoading } = useQuizQuestions(quiz.id);
  const addQuestion = useAddQuestion(quiz.id);
  const deleteQuestion = useDeleteQuestion(quiz.id);
  const { data: bankData } = useQuestionBank();
  const addBankQuestion = useAddBankQuestionToQuiz(quiz.id);

  // Edit Quiz details state
  const [editTitle, setEditTitle] = useState(quiz.title);
  const [editCourse, setEditCourse] = useState(quiz.course);
  const [editDescription, setEditDescription] = useState(quiz.description);
  const [editInstructions, setEditInstructions] = useState(quiz.instructions);
  const [editDuration, setEditDuration] = useState<number | string>(quiz.duration_minutes);
  const [editMaxMarks, setEditMaxMarks] = useState<number | string>(quiz.max_marks);
  const [editPassingMarks, setEditPassingMarks] = useState<number | string>(
    quiz.passing_marks ?? ""
  );
  const [editMaxAttempts, setEditMaxAttempts] = useState<number | string>(quiz.max_attempts);

  // New Question form state
  const [qType, setQType] = useState<QuestionType>("mcq");
  const [qText, setQText] = useState("");
  const [qMarks, setQMarks] = useState<number | string>(1);
  const [qNegativeMarks, setQNegativeMarks] = useState<number | string>(0);
  const [qTopic, setQTopic] = useState("");
  const [qDifficulty, setQDifficulty] = useState<string>("medium");
  const [qIsBank, setQIsBank] = useState(false);

  // MCQ / MSQ options state
  const [options, setOptions] = useState<OptionItem[]>([
    { id: "opt_1", text: "" },
    { id: "opt_2", text: "" },
    { id: "opt_3", text: "" },
    { id: "opt_4", text: "" },
  ]);
  const [mcqCorrect, setMcqCorrect] = useState("opt_1");
  const [msqCorrect, setMsqCorrect] = useState<string[]>(["opt_1"]);

  // TF state
  const [tfCorrect, setTfCorrect] = useState("true");

  // FITB state
  const [fitbCorrect, setFitbCorrect] = useState("");

  // SHORT subjective state
  const [refAnswer, setRefAnswer] = useState("");
  const [evalCriteria, setEvalCriteria] = useState("");

  const handleUpdateQuiz = async () => {
    try {
      await updateQuiz.mutateAsync({
        id: quiz.id,
        title: editTitle,
        course: editCourse,
        description: editDescription,
        instructions: editInstructions,
        duration_minutes: Number(editDuration) || 30,
        max_marks: Number(editMaxMarks) || 50,
        passing_marks: editPassingMarks ? Number(editPassingMarks) : null,
        max_attempts: Number(editMaxAttempts) || 1,
      });
      notifications.show({
        color: "green",
        message: "Quiz updated successfully",
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Update failed",
        message: errorMessage(err),
      });
    }
  };

  const handleAddQuestion = async () => {
    if (!qText.trim()) {
      notifications.show({ color: "red", message: "Question text is required" });
      return;
    }

    let payloadCorrectAnswer: unknown = null;
    let payloadOptions: OptionItem[] | null = null;

    if (qType === "mcq") {
      payloadOptions = options.filter((o) => o.text.trim().length > 0);
      payloadCorrectAnswer = mcqCorrect;
    } else if (qType === "msq") {
      payloadOptions = options.filter((o) => o.text.trim().length > 0);
      payloadCorrectAnswer = msqCorrect;
    } else if (qType === "tf") {
      payloadCorrectAnswer = tfCorrect === "true";
    } else if (qType === "fitb") {
      payloadCorrectAnswer = fitbCorrect.trim();
    }

    try {
      await addQuestion.mutateAsync({
        question_type: qType,
        text: qText,
        marks: Number(qMarks) || 1,
        negative_marks: Number(qNegativeMarks) || 0,
        topic: qTopic,
        difficulty: (qDifficulty as Question["difficulty"]) || "",
        is_bank_question: qIsBank,
        options: payloadOptions,
        correct_answer: payloadCorrectAnswer,
        reference_answer: refAnswer,
        evaluation_criteria: evalCriteria,
      });

      notifications.show({ color: "green", message: "Question added to quiz" });
      setQText("");
      setRefAnswer("");
      setEvalCriteria("");
      setFitbCorrect("");
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Failed to add question",
        message: errorMessage(err),
      });
    }
  };

  const handleImportBankQuestion = async (bankId: number) => {
    try {
      await addBankQuestion.mutateAsync(bankId);
      notifications.show({
        color: "green",
        message: "Question imported from bank into this quiz",
      });
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Import failed",
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
          Manage Quiz: {quiz.title} ({quiz.course})
        </Text>
      }
      size="xl"
    >
      <Tabs defaultValue="questions">
        <Tabs.List mb="md">
          <Tabs.Tab value="questions">Questions ({questionsData?.results.length ?? 0})</Tabs.Tab>
          <Tabs.Tab value="add_question">Add Question</Tabs.Tab>
          <Tabs.Tab value="bank">Import from Bank</Tabs.Tab>
          <Tabs.Tab value="settings">Quiz Settings</Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Current Questions */}
        <Tabs.Panel value="questions">
          <Stack gap="md">
            {questionsLoading ? (
              <Text size="sm" c="dimmed">
                Loading questions...
              </Text>
            ) : questionsData?.results.length === 0 ? (
              <Paper p="xl" withBorder style={{ textAlign: "center" }}>
                <Text fw={600} mb="xs">
                  No Questions Added Yet
                </Text>
                <Text size="sm" c="dimmed">
                  Switch to the 'Add Question' or 'Import from Bank' tabs to populate this quiz.
                </Text>
              </Paper>
            ) : (
              questionsData?.results.map((q, idx) => (
                <Card key={q.id} withBorder padding="sm" radius="md">
                  <Group justify="space-between" mb="xs">
                    <Group gap="xs">
                      <Badge variant="filled" size="sm">
                        Q{idx + 1}
                      </Badge>
                      <Badge variant="light" size="sm">
                        {q.question_type.toUpperCase()}
                      </Badge>
                      <Badge color="blue" variant="subtle" size="sm">
                        {q.marks} marks
                      </Badge>
                      {q.negative_marks > 0 && (
                        <Badge color="red" variant="subtle" size="sm">
                          -{q.negative_marks} neg
                        </Badge>
                      )}
                      {q.topic && (
                        <Badge color="gray" variant="outline" size="sm">
                          {q.topic}
                        </Badge>
                      )}
                    </Group>
                    <ActionIcon
                      color="red"
                      variant="subtle"
                      size="sm"
                      onClick={() => deleteQuestion.mutate(q.id)}
                    >
                      <FaTrash size={12} />
                    </ActionIcon>
                  </Group>
                  <Text size="sm" fw={500} mb="xs">
                    {q.text}
                  </Text>
                  {q.options && q.options.length > 0 && (
                    <SimpleGrid cols={2} spacing="xs" mt="xs">
                      {q.options.map((opt) => (
                        <Paper
                          key={opt.id}
                          p="xs"
                          withBorder
                          bg={
                            String(q.correct_answer) === opt.id ||
                            (Array.isArray(q.correct_answer) && q.correct_answer.includes(opt.id))
                              ? "var(--mantine-color-green-0)"
                              : undefined
                          }
                        >
                          <Text size="xs">
                            <Text span fw={600}>
                              {opt.id}:
                            </Text>{" "}
                            {opt.text}
                          </Text>
                        </Paper>
                      ))}
                    </SimpleGrid>
                  )}
                  {q.question_type === "short" && (
                    <Text size="xs" c="dimmed" mt="xs">
                      Ref answer: {q.reference_answer || "None provided"}
                    </Text>
                  )}
                </Card>
              ))
            )}
          </Stack>
        </Tabs.Panel>

        {/* Tab 2: Add New Question */}
        <Tabs.Panel value="add_question">
          <Stack gap="md">
            <FormRow>
              <Field span={4}>
                <Select
                  label="Question Type"
                  data={[
                    { value: "mcq", label: "Multiple Choice (MCQ)" },
                    { value: "msq", label: "Multiple Select (MSQ)" },
                    { value: "tf", label: "True / False" },
                    { value: "fitb", label: "Fill in the Blanks" },
                    { value: "short", label: "Short Answer (Subjective)" },
                  ]}
                  value={qType}
                  onChange={(val) => setQType((val as QuestionType) || "mcq")}
                />
              </Field>
              <Field span={4}>
                <NumberInput
                  label="Marks"
                  min={0.5}
                  value={qMarks}
                  onChange={(v) => setQMarks(v)}
                />
              </Field>
              <Field span={4}>
                <NumberInput
                  label="Negative Marks"
                  min={0}
                  value={qNegativeMarks}
                  onChange={(v) => setQNegativeMarks(v)}
                />
              </Field>
            </FormRow>

            <FormRow>
              <Field span={6}>
                <TextInput
                  label="Topic / Category"
                  placeholder="e.g. Data Structures, Networking"
                  value={qTopic}
                  onChange={(e) => setQTopic(e.currentTarget.value)}
                />
              </Field>
              <Field span={6}>
                <Select
                  label="Difficulty Level"
                  data={[
                    { value: "easy", label: "Easy" },
                    { value: "medium", label: "Medium" },
                    { value: "hard", label: "Hard" },
                  ]}
                  value={qDifficulty}
                  onChange={(val) => setQDifficulty(val || "medium")}
                />
              </Field>
            </FormRow>

            <Textarea
              label="Question Text"
              placeholder="Enter the full question statement..."
              minRows={3}
              required
              value={qText}
              onChange={(e) => setQText(e.currentTarget.value)}
            />

            {/* MCQ Options */}
            {qType === "mcq" && (
              <Stack gap="xs">
                <Text size="sm" fw={600}>
                  Options & Correct Answer
                </Text>
                <Radio.Group value={mcqCorrect} onChange={setMcqCorrect}>
                  <Stack gap="xs">
                    {options.map((opt, i) => (
                      <Group key={opt.id} wrap="nowrap">
                        <Radio value={opt.id} />
                        <TextInput
                          style={{ flex: 1 }}
                          placeholder={`Option ${i + 1}`}
                          value={opt.text}
                          onChange={(e) => {
                            const val = e.currentTarget.value;
                            setOptions((prev) =>
                              prev.map((o, idx) => (idx === i ? { ...o, text: val } : o))
                            );
                          }}
                        />
                      </Group>
                    ))}
                  </Stack>
                </Radio.Group>
              </Stack>
            )}

            {/* MSQ Options */}
            {qType === "msq" && (
              <Stack gap="xs">
                <Text size="sm" fw={600}>
                  Options & Correct Answers (Select all that apply)
                </Text>
                <Stack gap="xs">
                  {options.map((opt, i) => (
                    <Group key={opt.id} wrap="nowrap">
                      <Checkbox
                        checked={msqCorrect.includes(opt.id)}
                        onChange={(e) => {
                          if (e.currentTarget.checked) {
                            setMsqCorrect([...msqCorrect, opt.id]);
                          } else {
                            setMsqCorrect(msqCorrect.filter((x) => x !== opt.id));
                          }
                        }}
                      />
                      <TextInput
                        style={{ flex: 1 }}
                        placeholder={`Option ${i + 1}`}
                        value={opt.text}
                        onChange={(e) => {
                          const val = e.currentTarget.value;
                          setOptions((prev) =>
                            prev.map((o, idx) => (idx === i ? { ...o, text: val } : o))
                          );
                        }}
                      />
                    </Group>
                  ))}
                </Stack>
              </Stack>
            )}

            {/* True/False */}
            {qType === "tf" && (
              <Select
                label="Correct Answer"
                data={[
                  { value: "true", label: "True" },
                  { value: "false", label: "False" },
                ]}
                value={tfCorrect}
                onChange={(val) => setTfCorrect(val || "true")}
              />
            )}

            {/* Fill in the Blanks */}
            {qType === "fitb" && (
              <TextInput
                label="Accepted Answer (Exact Match / Auto-Graded)"
                placeholder="e.g. O(log n)"
                value={fitbCorrect}
                onChange={(e) => setFitbCorrect(e.currentTarget.value)}
              />
            )}

            {/* Subjective */}
            {qType === "short" && (
              <Stack gap="xs">
                <Textarea
                  label="Reference Answer"
                  placeholder="Key concepts or ideal answer..."
                  minRows={2}
                  value={refAnswer}
                  onChange={(e) => setRefAnswer(e.currentTarget.value)}
                />
                <Textarea
                  label="Evaluation Criteria / Grading Rubric"
                  placeholder="Marks allocation criteria for professor & AI grading..."
                  minRows={2}
                  value={evalCriteria}
                  onChange={(e) => setEvalCriteria(e.currentTarget.value)}
                />
              </Stack>
            )}

            <Switch
              label="Save to Question Bank for future reuse"
              checked={qIsBank}
              onChange={(e) => setQIsBank(e.currentTarget.checked)}
            />

            <Button
              loading={addQuestion.isPending}
              onClick={handleAddQuestion}
              leftSection={<FaPlus size={12} />}
            >
              Add Question to Quiz
            </Button>
          </Stack>
        </Tabs.Panel>

        {/* Tab 3: Import from Question Bank */}
        <Tabs.Panel value="bank">
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              Select questions from your institution's question bank to import into this quiz.
            </Text>
            {bankData?.results.length === 0 ? (
              <Text size="sm">No questions available in the question bank.</Text>
            ) : (
              bankData?.results.map((bq) => (
                <Card key={bq.id} withBorder padding="sm" radius="md">
                  <Group justify="space-between">
                    <Stack gap={2}>
                      <Group gap="xs">
                        <Badge size="xs">{bq.question_type.toUpperCase()}</Badge>
                        <Badge size="xs" color="blue">
                          {bq.marks} marks
                        </Badge>
                        {bq.topic && (
                          <Badge size="xs" color="gray">
                            {bq.topic}
                          </Badge>
                        )}
                      </Group>
                      <Text size="sm" fw={500}>
                        {bq.text}
                      </Text>
                    </Stack>
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<FaUpload size={12} />}
                      loading={addBankQuestion.isPending}
                      onClick={() => handleImportBankQuestion(bq.id)}
                    >
                      Import
                    </Button>
                  </Group>
                </Card>
              ))
            )}
          </Stack>
        </Tabs.Panel>

        {/* Tab 4: Quiz Settings */}
        <Tabs.Panel value="settings">
          <Stack gap="md">
            <FormRow>
              <Field span={6}>
                <TextInput
                  label="Quiz Title"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.currentTarget.value)}
                />
              </Field>
              <Field span={6}>
                <TextInput
                  label="Course Code"
                  value={editCourse}
                  onChange={(e) => setEditCourse(e.currentTarget.value)}
                />
              </Field>
            </FormRow>
            <FormRow>
              <Field span={6}>
                <NumberInput
                  label="Duration (Minutes)"
                  min={1}
                  value={editDuration}
                  onChange={(v) => setEditDuration(v)}
                />
              </Field>
              <Field span={6}>
                <NumberInput
                  label="Max Marks"
                  min={0}
                  value={editMaxMarks}
                  onChange={(v) => setEditMaxMarks(v)}
                />
              </Field>
            </FormRow>
            <FormRow>
              <Field span={6}>
                <NumberInput
                  label="Passing Marks"
                  min={0}
                  value={editPassingMarks}
                  onChange={(v) => setEditPassingMarks(v)}
                />
              </Field>
              <Field span={6}>
                <NumberInput
                  label="Max Attempts"
                  min={1}
                  value={editMaxAttempts}
                  onChange={(v) => setEditMaxAttempts(v)}
                />
              </Field>
            </FormRow>
            <Textarea
              label="Description"
              value={editDescription}
              onChange={(e) => setEditDescription(e.currentTarget.value)}
            />
            <Textarea
              label="Instructions"
              value={editInstructions}
              onChange={(e) => setEditInstructions(e.currentTarget.value)}
            />
            <Divider />
            <Button
              loading={updateQuiz.isPending}
              onClick={handleUpdateQuiz}
              style={{ alignSelf: "flex-end" }}
            >
              Save Quiz Changes
            </Button>
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Modal>
  );
}
