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
import { useResumptionsQueue, useVerifyResumption } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function ResumptionsPage() {
  const { data: queue, isPending, error } = useResumptionsQueue();
  const verifyMut = useVerifyResumption();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [remark, setRemark] = useState<string>("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleVerifySubmit() {
    if (!selectedReq) return;
    verifyMut.mutate(
      { id: selectedReq.id, remark },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Resumption Verified",
            message: `Duty resumption verified for leave request #${selectedReq.id}. Balance adjusted and request closed.`,
          });
          setSelectedReq(null);
          setRemark("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Verification Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Duty Resumptions"
        subtitle="Verify employee reports of duty resumption after leave"
      />

      <Card padding="lg" withBorder>
        <DataTable<LeaveRequest>
          rows={queue ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No pending resumptions", description: "There are no duty resumptions waiting for verification." }}
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
              header: "Sanctioned Period",
              render: (r) => (
                <Text size="sm">
                  {r.starts_on} to {r.ends_on}
                </Text>
              ),
            },
            {
              key: "resumed",
              header: "Resumed On",
              render: (r) => (
                <Badge color="teal" variant="light">
                  {r.resumed_on ?? "Not reported"}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "Action",
              render: (r) => (
                <Button
                  size="xs"
                  color="teal"
                  onClick={() => setSelectedReq(r)}
                >
                  Verify & Close
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={Boolean(selectedReq)}
        onClose={() => setSelectedReq(null)}
        title="Verify Duty Resumption"
      >
        <Stack gap="md">
          <Text size="sm">
            Verify duty resumption for request #{selectedReq?.id}? Resumed on: {selectedReq?.resumed_on}.
            If the employee returned early, unconsumed days will be restored to their balance.
          </Text>
          <Textarea
            label="Verification Remark"
            placeholder="Remarks..."
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setSelectedReq(null)}>Cancel</Button>
            <Button
              color="teal"
              loading={verifyMut.isPending}
              onClick={handleVerifySubmit}
            >
              Confirm Verification
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
