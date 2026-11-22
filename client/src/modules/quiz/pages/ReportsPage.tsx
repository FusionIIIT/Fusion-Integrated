import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import {
  FaChartPie,
  FaCheckCircle,
  FaDownload,
  FaFileAlt,
  FaUsers,
} from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useQuizReport, useQuizzes } from "../api/hooks";
import type { QuizAttempt } from "../api/types";

export default function ReportsPage() {
  const { data: quizzesData, isPending: quizzesLoading, error: quizzesError } = useQuizzes();
  const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);

  // Auto-select first quiz if available
  useEffect(() => {
    if (!selectedQuizId && quizzesData?.results && quizzesData.results.length > 0 && quizzesData.results[0]) {
      setSelectedQuizId(String(quizzesData.results[0].id));
    }
  }, [quizzesData, selectedQuizId]);

  const quizIdNumber = selectedQuizId ? Number(selectedQuizId) : undefined;
  const { data: report, isPending: reportLoading, error: reportError } = useQuizReport(quizIdNumber);

  const quizOptions = (quizzesData?.results ?? []).map((q) => ({
    value: String(q.id),
    label: `${q.title} (${q.course})`,
  }));

  const handleExportCsv = () => {
    if (!report || !report.submissions.length) return;
    const headers = [
      "Student ID",
      "Attempt #",
      "Status",
      "Score",
      "Percentage",
      "Passed",
      "Time Taken (s)",
      "Tab Violations",
      "Submitted At",
    ];
    const rows = report.submissions.map((s) => [
      s.user_id,
      s.attempt_number,
      s.status,
      s.score ?? "",
      s.percentage !== null ? `${s.percentage}%` : "",
      s.passed === null ? "Pending" : s.passed ? "Pass" : "Fail",
      s.time_taken_seconds ?? "",
      s.tab_violations,
      s.submitted_at ? new Date(s.submitted_at).toISOString() : "",
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((r) => r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `quiz_${report.quiz_id}_report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
        title="Quiz Reports & Analytics"
        subtitle="Performance analytics, grade distribution, and student submission records"
        action={
          report && report.submissions.length > 0 && (
            <Button
              variant="light"
              leftSection={<FaDownload size={12} />}
              onClick={handleExportCsv}
            >
              Export CSV
            </Button>
          )
        }
      />

      <Card padding="md" mb="lg" radius="md" withBorder>
        <Select
          label="Select Quiz to View Analytics"
          placeholder="Choose an assessment"
          data={quizOptions}
          value={selectedQuizId}
          onChange={setSelectedQuizId}
          disabled={quizzesLoading}
          style={{ maxWidth: 400 }}
        />
      </Card>

      {reportError ? (
        <ErrorState error={reportError} />
      ) : !selectedQuizId ? (
        <Card padding="xl" radius="md" withBorder style={{ textAlign: "center" }}>
          <Text c="dimmed">Please select a quiz to generate analytics.</Text>
        </Card>
      ) : (
        <Stack gap="lg">
          {/* Key Metric Summary Cards */}
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Submissions
                </Text>
                <FaUsers size={16} color="var(--mantine-color-blue-6)" />
              </Group>
              <Text fw={700} size="xl" mt="xs">
                {report?.total_submissions ?? 0}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Student attempts recorded
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Average Score
                </Text>
                <FaChartPie size={16} color="var(--mantine-color-teal-6)" />
              </Group>
              <Text fw={700} size="xl" mt="xs">
                {report?.average_score !== null && report?.average_score !== undefined
                  ? `${report.average_score}`
                  : "—"}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Across all evaluated submissions
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Score Range (High / Low)
                </Text>
                <FaFileAlt size={16} color="var(--mantine-color-indigo-6)" />
              </Group>
              <Text fw={700} size="xl" mt="xs">
                {report?.highest_score !== null && report?.highest_score !== undefined
                  ? `${report.highest_score}`
                  : "—"}{" "}
                /{" "}
                {report?.lowest_score !== null && report?.lowest_score !== undefined
                  ? `${report.lowest_score}`
                  : "—"}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Highest & lowest scores obtained
              </Text>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group justify="space-between">
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Pass Percentage
                </Text>
                <FaCheckCircle size={16} color="var(--mantine-color-green-6)" />
              </Group>
              <Text fw={700} size="xl" mt="xs">
                {report?.pass_percentage !== null && report?.pass_percentage !== undefined
                  ? `${report.pass_percentage}%`
                  : "—"}
              </Text>
              <Text size="xs" c="dimmed" mt={4}>
                Qualified passing threshold
              </Text>
            </Paper>
          </SimpleGrid>

          {/* Submissions Table */}
          <Card padding="lg" radius="md" withBorder>
            <DataTable<QuizAttempt>
              rows={report?.submissions ?? []}
              loading={reportLoading}
              rowKey={(r) => r.id}
              empty={{
                icon: FaChartPie,
                title: "No Data Available",
                description: "Submissions will appear here once students attempt this assessment.",
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
                      {r.score !== null ? `${r.score} marks` : "—"}
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
                  header: "Pass / Fail",
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
                  key: "time",
                  header: "Time Taken",
                  render: (r) => (
                    <Text size="xs">
                      {r.time_taken_seconds
                        ? `${Math.round(r.time_taken_seconds / 60)} mins`
                        : "—"}
                    </Text>
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
              ]}
            />
          </Card>
        </Stack>
      )}
    </Container>
  );
}
