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
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReviewDecision, useReviewQueue } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function ReviewQueuePage() {
  const { data: queue, isPending, error } = useReviewQueue();
  const decisionMut = useReviewDecision();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [approve, setApprove] = useState<boolean>(true);
  const [remark, setRemark] = useState<string>("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleDecisionSubmit() {
    if (!selectedReq) return;
    decisionMut.mutate(
      { id: selectedReq.id, approve, remark },
      {
        onSuccess: () => {
          notifications.show({
            color: approve ? "green" : "red",
            title: approve ? "Request Approved / Recommended" : "Request Rejected",
            message: `Review recorded for leave request #${selectedReq.id}.`,
          });
          setSelectedReq(null);
          setRemark("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Review Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Review Queue"
        subtitle="Department / Unit head review of submitted leave applications"
      />

      <Card padding="lg" withBorder>
        <DataTable<LeaveRequest>
          rows={queue ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "Review queue is clear", description: "No leave applications awaiting your review." }}
          minWidth={850}
          columns={[
            {
              key: "id",
              header: "Request ID",
              render: (r) => <Text fw={600}>#{r.id}</Text>,
            },
            {
              key: "user",
              header: "Employee ID",
              render: (r) => <Text size="sm">User #{r.user_id}</Text>,
            },
            {
              key: "category",
              header: "Category",
              render: (r) => <Badge color="blue">{r.category}</Badge>,
            },
            {
              key: "dates",
              header: "Leave Dates",
              render: (r) => (
                <Text size="sm">
                  {r.starts_on} to {r.ends_on} ({r.deductible_days} days)
                </Text>
              ),
            },
            {
              key: "reason",
              header: "Reason",
              render: (r) => <Text size="sm" lineClamp={2}>{r.reason}</Text>,
            },
            {
              key: "actions",
              header: "Decision",
              render: (r) => (
                <Group gap="xs">
                  <Button
                    size="xs"
                    color="green"
                    onClick={() => {
                      setSelectedReq(r);
                      setApprove(true);
                    }}
                  >
                    Recommend / Approve
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    onClick={() => {
                      setSelectedReq(r);
                      setApprove(false);
                    }}
                  >
                    Reject
                  </Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={Boolean(selectedReq)}
        onClose={() => setSelectedReq(null)}
        title={approve ? "Recommend / Approve Application" : "Reject Application"}
      >
        <Stack gap="md">
          <Text size="sm">
            {approve
              ? `Recommend or approve leave request #${selectedReq?.id}? For CL/RH, this will grant sanction. For higher categories, this forwards to Establishment routing.`
              : `Reject leave request #${selectedReq?.id}? This will close the application.`}
          </Text>
          <Textarea
            label="Review Remarks"
            required={!approve}
            placeholder="Add comments or justification..."
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color={approve ? "green" : "red"}
              loading={decisionMut.isPending}
              onClick={handleDecisionSubmit}
            >
              Submit Decision
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
