import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaComments, FaPen, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDepartments,
  useFeedback,
  useResolveFeedback,
  useReviewFeedback,
} from "../api/hooks";
import { DepartmentStatusBadge } from "../components/DepartmentStatusBadge";
import { SubmitFeedbackModal } from "../components/SubmitFeedbackModal";

export default function FeedbackPage() {
  const { can } = useAuth();
  const { data: depts } = useDepartments();
  const defaultDept = depts?.[0];
  const deptId = defaultDept?.id;

  const { data: feedbackList, isPending, error } = useFeedback(deptId);
  const reviewFb = useReviewFeedback();
  const resolveFb = useResolveFeedback();

  const [submitting, setSubmitting] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>("all");

  const canSubmit = can("department.feedback.submit");
  const canManage = can("department.detail.update") || can("department.detail.propose");

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = (feedbackList || []).filter((fb) => {
    if (filterCategory === "all") return true;
    return fb.category === filterCategory;
  });

  const handleReview = async (id: number) => {
    try {
      await reviewFb.mutateAsync({ id, category: "Reviewed / Academic" });
      notifications.show({
        title: "Feedback Reviewed",
        message: "Status updated to reviewed.",
        color: "teal",
      });
    } catch {
      notifications.show({
        title: "Action failed",
        message: "Could not review feedback.",
        color: "red",
      });
    }
  };

  const handleResolve = async (id: number, status: "resolved" | "closed") => {
    try {
      await resolveFb.mutateAsync({ id, status });
      notifications.show({
        title: `Feedback ${status}`,
        message: `Feedback marked as ${status}.`,
        color: "teal",
      });
    } catch {
      notifications.show({
        title: "Action failed",
        message: "Could not update status.",
        color: "red",
      });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Department Feedback & Grievance"
        subtitle="Confidential academic, infrastructure, and laboratory feedback"
        action={
          canSubmit && deptId && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setSubmitting(true)}
            >
              Submit Feedback
            </Button>
          )
        }
      />

      <Group justify="space-between" mb="md">
        <Select
          label="Filter by Category"
          size="xs"
          data={[
            { value: "all", label: "All categories" },
            { value: "academic", label: "Academic" },
            { value: "laboratory", label: "Laboratory" },
            { value: "administrative", label: "Administrative" },
            { value: "infrastructure", label: "Infrastructure" },
          ]}
          value={filterCategory}
          onChange={(v) => setFilterCategory(v || "all")}
          style={{ width: 180 }}
        />
        <Text size="xs" c="dimmed" mt="auto">
          Showing {rows.length} submission(s)
        </Text>
      </Group>

      {isPending && <Text c="dimmed">Loading feedback…</Text>}

      {!isPending && rows.length === 0 && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={6}>
            <FaComments size={28} color="var(--mantine-color-gray-5)" />
            <Title order={4}>No feedback records</Title>
            <Text size="sm" c="dimmed">
              No feedback or grievances submitted under this filter.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((fb) => (
          <Card key={fb.id} padding="lg" withBorder>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={6} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700}>{fb.subject}</Text>
                  <DepartmentStatusBadge status={fb.status} />
                  {fb.category && (
                    <Badge variant="outline" size="xs">
                      {fb.category}
                    </Badge>
                  )}
                </Group>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {fb.body}
                </Text>
                <Text size="xs" c="dimmed">
                  Submitted by User #{fb.submitter_user_id} ·{" "}
                  {new Date(fb.created_at).toLocaleString()}
                </Text>
              </Stack>

              {canManage && (
                <Group gap="xs">
                  {fb.status === "submitted" && (
                    <Button
                      size="compact-xs"
                      variant="light"
                      color="blue"
                      leftSection={<FaPen size={10} />}
                      loading={reviewFb.isPending}
                      onClick={() => handleReview(fb.id)}
                    >
                      Review
                    </Button>
                  )}
                  {(fb.status === "submitted" || fb.status === "reviewed") && (
                    <Button
                      size="compact-xs"
                      color="teal"
                      leftSection={<FaCheck size={10} />}
                      loading={resolveFb.isPending}
                      onClick={() => handleResolve(fb.id, "resolved")}
                    >
                      Resolve
                    </Button>
                  )}
                </Group>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      {deptId && (
        <SubmitFeedbackModal
          opened={submitting}
          onClose={() => setSubmitting(false)}
          departmentId={deptId}
        />
      )}
    </Container>
  );
}
