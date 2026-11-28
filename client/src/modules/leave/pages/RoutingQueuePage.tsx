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
import { useRoutingDecision, useRoutingQueue } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function RoutingQueuePage() {
  const { data: queue, isPending, error } = useRoutingQueue();
  const routeMut = useRoutingDecision();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [remark, setRemark] = useState<string>("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleRoutingSubmit() {
    if (!selectedReq) return;
    routeMut.mutate(
      { id: selectedReq.id, remark },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Request Routed",
            message: `Leave request #${selectedReq.id} routed to sanctioning authority.`,
          });
          setSelectedReq(null);
          setRemark("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Routing Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Routing Queue"
        subtitle="Establishment section verification and routing of recommended leave"
      />

      <Card padding="lg" withBorder>
        <DataTable<LeaveRequest>
          rows={queue ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "Routing queue is clear", description: "No applications awaiting forwarding to sanctioning authority." }}
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
              header: "Period",
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
              header: "Action",
              render: (r) => (
                <Button
                  size="xs"
                  color="blue"
                  onClick={() => setSelectedReq(r)}
                >
                  Forward to Sanction
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={Boolean(selectedReq)}
        onClose={() => setSelectedReq(null)}
        title="Forward to Sanctioning Authority"
      >
        <Stack gap="md">
          <Text size="sm">
            Forward request #{selectedReq?.id} to the competent sanctioning authority?
          </Text>
          <Textarea
            label="Verification Note / Remark"
            placeholder="Add establishment verification remarks..."
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color="blue"
              loading={routeMut.isPending}
              onClick={handleRoutingSubmit}
            >
              Confirm Forwarding
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
