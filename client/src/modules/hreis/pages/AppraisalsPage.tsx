import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Paper,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaFileAlt, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAppraisals, useSubmitAppraisal } from "../api/hooks";
import type { AppraisalSubmission } from "../api/types";

export default function AppraisalsPage() {
  const { data: appraisals, isPending, error } = useAppraisals();
  const submitMutation = useSubmitAppraisal();
  const { can } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<AppraisalSubmission | null>(null);

  // Form states
  const [academicYear, setAcademicYear] = useState<string>("2025-2026");
  const [coursesTaught, setCoursesTaught] = useState<string>("");
  const [publications, setPublications] = useState<string>("");
  const [sponsoredProjects, setSponsoredProjects] = useState<string>("");
  const [summary, setSummary] = useState<string>("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleSubmit = (draft = false) => {
    if (!academicYear) {
      notifications.show({ title: "Validation Error", message: "Academic year is required", color: "red" });
      return;
    }

    const content = {
      courses_taught: coursesTaught.split("\n").filter(Boolean),
      publications: publications.split("\n").filter(Boolean),
      sponsored_projects: sponsoredProjects.split("\n").filter(Boolean),
      self_appraisal_summary: summary,
    };

    submitMutation.mutate(
      { academic_year: academicYear, content, draft },
      {
        onSuccess: () => {
          notifications.show({
            title: draft ? "Draft Saved" : "Appraisal Submitted",
            message: draft
              ? "Your self-appraisal draft has been saved."
              : "Appraisal submitted for peer review and director evaluation.",
            color: "teal",
          });
          setModalOpen(false);
        },
        onError: (err) => {
          notifications.show({
            title: "Submission Error",
            message: errorMessage(err),
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Annual Performance Appraisals"
        subtitle="Faculty and staff yearly appraisal submissions, peer review evaluation, and final appraisal closure (BR-HR-012, BR-HR-015)"
        action={
          can("hr_eis.appraisal.submit") && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setModalOpen(true)}
              color="teal"
            >
              Submit Appraisal
            </Button>
          )
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<AppraisalSubmission>
          rows={appraisals ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          empty={{
            icon: FaFileAlt,
            title: "No appraisal submissions",
            description: "No annual appraisal records found.",
          }}
          columns={[
            {
              key: "academic_year",
              header: "Academic Year",
              render: (r) => <Text fw={600} size="sm">{r.academic_year}</Text>,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "final_score",
              header: "Final Score",
              render: (r) => (
                <Text size="sm" fw={700} c={r.final_score != null ? "teal" : "dimmed"}>
                  {r.final_score != null ? `${r.final_score} / 100` : "Under Evaluation"}
                </Text>
              ),
            },
            {
              key: "submitted_at",
              header: "Submission Date",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {new Date(r.created_at).toLocaleDateString()}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Details",
              render: (r) => (
                <Button size="xs" variant="light" onClick={() => setDetailTarget(r)}>
                  View Report
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* Submit Appraisal Modal */}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Annual Performance Appraisal Self-Assessment"
        size="lg"
      >
        <Stack gap="md">
          <Select
            label="Academic Year"
            required
            value={academicYear}
            onChange={(v) => v && setAcademicYear(v)}
            data={["2023-2024", "2024-2025", "2025-2026", "2026-2027"]}
          />

          <Textarea
            label="Teaching Engagement & Courses Taught"
            placeholder="List course codes and titles (one per line)..."
            rows={3}
            value={coursesTaught}
            onChange={(e) => setCoursesTaught(e.target.value)}
          />

          <Textarea
            label="Research Publications & Papers"
            placeholder="List papers, conferences, and journals published (one per line)..."
            rows={3}
            value={publications}
            onChange={(e) => setPublications(e.target.value)}
          />

          <Textarea
            label="Sponsored Projects & Grants"
            placeholder="List ongoing and completed research projects..."
            rows={2}
            value={sponsoredProjects}
            onChange={(e) => setSponsoredProjects(e.target.value)}
          />

          <Textarea
            label="Self-Appraisal Executive Summary"
            placeholder="Highlight major achievements, contributions, and key objectives..."
            rows={4}
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="outline"
              loading={submitMutation.isPending}
              onClick={() => handleSubmit(true)}
            >
              Save Draft
            </Button>
            <Button
              color="teal"
              loading={submitMutation.isPending}
              onClick={() => handleSubmit(false)}
            >
              Submit Appraisal
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Detail Modal */}
      <Modal
        opened={detailTarget != null}
        onClose={() => setDetailTarget(null)}
        title={`Annual Appraisal: ${detailTarget?.academic_year}`}
        size="lg"
      >
        {detailTarget && (
          <Stack gap="md">
            <Group justify="space-between">
              <StatusBadge status={detailTarget.status} />
              {detailTarget.final_score != null && (
                <Badge size="lg" color="teal">
                  Score: {detailTarget.final_score} / 100
                </Badge>
              )}
            </Group>

            <Paper withBorder p="md" radius="sm">
              <Title order={6} mb="xs">Self-Appraisal Content</Title>
              <pre style={{ fontSize: "12px", whiteSpace: "pre-wrap", margin: 0 }}>
                {JSON.stringify(detailTarget.content, null, 2)}
              </pre>
            </Paper>

            {detailTarget.reviews?.length > 0 && (
              <Paper withBorder p="md" radius="sm">
                <Title order={6} mb="xs">Peer Reviews</Title>
                <Stack gap="xs">
                  {detailTarget.reviews.map((rev, i) => (
                    <Paper key={i} withBorder p="xs" radius="xs">
                      <Group justify="space-between">
                        <Text size="xs" fw={600}>Score: {rev.score} / 100</Text>
                        <Text size="xs" c="dimmed">Reviewer #{rev.reviewer_id}</Text>
                      </Group>
                      <Text size="xs" mt={2}>"{rev.comments}"</Text>
                    </Paper>
                  ))}
                </Stack>
              </Paper>
            )}

            {detailTarget.final_remarks && (
              <Paper withBorder p="md" radius="sm" bg="gray.0">
                <Title order={6} mb="xs">Final Director Remarks</Title>
                <Text size="sm">{detailTarget.final_remarks}</Text>
              </Paper>
            )}
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
