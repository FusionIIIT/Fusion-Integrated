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
import { useSanctionDecision, useSanctionQueue } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function SanctionQueuePage() {
  const { data: queue, isPending, error } = useSanctionQueue();
  const sanctionMut = useSanctionDecision();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [approve, setApprove] = useState<boolean>(true);
  const [remark, setRemark] = useState<string>("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleDecisionSubmit() {
    if (!selectedReq) return;
    sanctionMut.mutate(
      { id: selectedReq.id, approve, remark },
      {
        onSuccess: () => {
          notifications.show({
            color: approve ? "green" : "red",
            title: approve ? "Leave Sanctioned" : "Leave Rejected",
            message: `Sanction decision recorded for leave request #${selectedReq.id}.`,
          });
          setSelectedReq(null);
          setRemark("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Sanction Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Sanction Queue"
        subtitle="Competent authority final sanctioning of leave applications"
      />

      <Card padding="lg" withBorder>
        <DataTable<LeaveRequest>
          rows={queue ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "Sanction queue is clear", description: "No applications awaiting your final sanction decision." }}
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
              header: "Duration",
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
                    Sanction
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
        title={approve ? "Sanction Leave Application" : "Reject Leave Application"}
      >
        <Stack gap="md">
          <Text size="sm">
            {approve
              ? `Grant final sanction for leave request #${selectedReq?.id}? This will consume deductible days from the employee's balance.`
              : `Reject leave request #${selectedReq?.id}?`}
          </Text>
          <Textarea
            label="Sanction Order / Remarks"
            required={!approve}
            placeholder="Official remarks..."
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color={approve ? "green" : "red"}
              loading={sanctionMut.isPending}
              onClick={handleDecisionSubmit}
            >
              Confirm Decision
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
