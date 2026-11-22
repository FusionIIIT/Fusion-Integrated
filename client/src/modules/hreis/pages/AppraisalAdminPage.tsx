import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserCheck, FaUsers } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAppraisals, useAssignReviewers } from "../api/hooks";
import type { AppraisalSubmission } from "../api/types";

export default function AppraisalAdminPage() {
  const { data: appraisals, isPending, error } = useAppraisals();
  const assignMutation = useAssignReviewers();

  const [modalOpen, setModalOpen] = useState(false);
  const [targetId, setTargetId] = useState<number | null>(null);
  const [reviewerIdsInput, setReviewerIdsInput] = useState<string>("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleAssign = () => {
    if (!targetId || !reviewerIdsInput) {
      notifications.show({
        title: "Validation Error",
        message: "Please enter comma-separated reviewer user IDs.",
        color: "red",
      });
      return;
    }

    const reviewer_ids = reviewerIdsInput
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => !isNaN(n) && n > 0);

    if (reviewer_ids.length === 0) {
      notifications.show({
        title: "Invalid IDs",
        message: "Please specify valid numeric user IDs.",
        color: "red",
      });
      return;
    }

    assignMutation.mutate(
      { id: targetId, reviewer_ids },
      {
        onSuccess: () => {
          notifications.show({
            title: "Reviewers Assigned",
            message: "Appraisal moved to Under Review and reviewers notified.",
            color: "teal",
          });
          setModalOpen(false);
          setTargetId(null);
          setReviewerIdsInput("");
        },
        onError: (err) => {
          notifications.show({
            title: "Assignment Error",
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
        title="Appraisal Coordination & Reviewer Assignment"
        subtitle="Coordinate annual peer reviews, assign evaluators, and track progress (BR-HR-013, BR-HR-014)"
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<AppraisalSubmission>
          rows={appraisals ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          empty={{
            icon: FaUsers,
            title: "No appraisal submissions",
            description: "No annual appraisals submitted yet for this cycle.",
          }}
          columns={[
            {
              key: "user_id",
              header: "Faculty / Staff",
              render: (r) => <Text size="sm" fw={600}>User #{r.user_id}</Text>,
            },
            {
              key: "academic_year",
              header: "Academic Year",
              render: (r) => <Text size="sm">{r.academic_year}</Text>,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "reviewers",
              header: "Assigned Reviewers",
              render: (r) =>
                r.assigned_reviewers?.length > 0 ? (
                  <Group gap={4}>
                    {r.assigned_reviewers.map((id) => (
                      <Badge key={id} size="xs" variant="outline">
                        #{id}
                      </Badge>
                    ))}
                  </Group>
                ) : (
                  <Text size="xs" c="dimmed">
                    Unassigned
                  </Text>
                ),
            },
            {
              key: "reviews_count",
              header: "Reviews Submitted",
              render: (r) => (
                <Text size="sm">
                  {r.reviews?.length ?? 0} / {r.assigned_reviewers?.length ?? 0}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Assignment",
              render: (r) => (
                <Button
                  size="xs"
                  variant="light"
                  color="blue"
                  leftSection={<FaUserCheck size={12} />}
                  onClick={() => {
                    setTargetId(r.id);
                    setReviewerIdsInput(r.assigned_reviewers?.join(", ") || "");
                    setModalOpen(true);
                  }}
                >
                  Assign Reviewers
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* Assign Reviewers Modal */}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Assign Peer Reviewers"
        size="md"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Enter the User IDs of faculty or committee members assigned to review this appraisal.
          </Text>

          <TextInput
            label="Reviewer User IDs (comma-separated)"
            placeholder="e.g. 102, 105, 110"
            required
            value={reviewerIdsInput}
            onChange={(e) => setReviewerIdsInput(e.target.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button color="blue" loading={assignMutation.isPending} onClick={handleAssign}>
              Confirm Assignment
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
