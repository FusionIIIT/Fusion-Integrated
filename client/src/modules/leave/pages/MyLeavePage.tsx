import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCancelLeave,
  useMyBalances,
  useMyRequests,
  useWithdrawLeave,
} from "../api/hooks";
import type { LeaveBalance, LeaveRequest } from "../api/types";

export default function MyLeavePage() {
  const { data: requests, isPending: reqPending, error: reqError } = useMyRequests();
  const { data: balances, isPending: balPending, error: balError } = useMyBalances();
  const withdrawMut = useWithdrawLeave();
  const cancelMut = useCancelLeave();

  const [selectedReq, setSelectedReq] = useState<LeaveRequest | null>(null);
  const [actionType, setActionType] = useState<"withdraw" | "cancel" | null>(null);
  const [remark, setRemark] = useState("");

  if (reqError) return <Container size="xl"><ErrorState error={reqError} /></Container>;
  if (balError) return <Container size="xl"><ErrorState error={balError} /></Container>;

  function handleActionSubmit() {
    if (!selectedReq || !actionType) return;
    const mutate = actionType === "withdraw" ? withdrawMut : cancelMut;
    mutate.mutate(
      { id: selectedReq.id, remark },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Success",
            message: `Leave request #${selectedReq.id} ${actionType === "withdraw" ? "withdrawn" : "cancelled"}.`,
          });
          setActionType(null);
          setSelectedReq(null);
          setRemark("");
        },
        onError: (e) => {
          notifications.show({
            color: "red",
            title: "Action Failed",
            message: errorMessage(e),
          });
        },
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="View your leave balances and track submitted applications"
      />

      <Stack gap="lg">
        <div>
          <Title order={4} mb="xs">Current Balances</Title>
          <SimpleGrid cols={{ base: 2, sm: 4, md: 6 }} spacing="sm">
            {(balances ?? []).map((b: LeaveBalance) => (
              <Card key={b.category} padding="sm" withBorder>
                <Text size="xs" c="dimmed" fw={600}>{b.category}</Text>
                <Text size="xl" fw={700}>{b.available}</Text>
                <Text size="xs" c="dimmed">Credited: {b.credited} | Used: {b.consumed}</Text>
              </Card>
            ))}
          </SimpleGrid>
        </div>

        <Card padding="lg" withBorder>
          <Title order={4} mb="md">My Leave Applications</Title>
          <DataTable<LeaveRequest>
            rows={requests ?? []}
            loading={reqPending || balPending}
            rowKey={(r) => r.id}
            empty={{ title: "No leave applications", description: "You have not submitted any leave applications yet." }}
            minWidth={800}
            columns={[
              {
                key: "id",
                header: "ID",
                render: (r) => <Text fw={600}>#{r.id}</Text>,
              },
              {
                key: "category",
                header: "Category",
                render: (r) => <Badge color="blue">{r.category}</Badge>,
              },
              {
                key: "dates",
                header: "Dates",
                render: (r) => (
                  <Text size="sm">
                    {r.starts_on} to {r.ends_on} ({r.deductible_days} days)
                  </Text>
                ),
              },
              {
                key: "state",
                header: "Status",
                render: (r) => <StatusBadge status={r.state} />,
              },
              {
                key: "reason",
                header: "Reason",
                render: (r) => <Text size="sm" lineClamp={1}>{r.reason}</Text>,
              },
              {
                key: "actions",
                header: "Actions",
                render: (r) => (
                  <Group gap="xs">
                    {["draft", "pending_substitute", "pending_review", "pending_routing", "pending_sanction"].includes(r.state) && (
                      <Button
                        size="xs"
                        variant="subtle"
                        color="red"
                        onClick={() => {
                          setSelectedReq(r);
                          setActionType("withdraw");
                        }}
                      >
                        Withdraw
                      </Button>
                    )}
                    {r.state === "sanctioned" && (
                      <Button
                        size="xs"
                        variant="subtle"
                        color="orange"
                        onClick={() => {
                          setSelectedReq(r);
                          setActionType("cancel");
                        }}
                      >
                        Cancel
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
          />
        </Card>
      </Stack>

      <Modal
        opened={Boolean(actionType)}
        onClose={() => {
          setActionType(null);
          setSelectedReq(null);
        }}
        title={actionType === "withdraw" ? "Withdraw Leave Application" : "Request Cancellation"}
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to {actionType} leave request #{selectedReq?.id}?
          </Text>
          <Textarea
            label="Remark / Reason"
            placeholder="Provide a reason..."
            value={remark}
            onChange={(e) => setRemark(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActionType(null)}>Cancel</Button>
            <Button
              color={actionType === "withdraw" ? "red" : "orange"}
              loading={withdrawMut.isPending || cancelMut.isPending}
              onClick={handleActionSubmit}
            >
              Confirm
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
