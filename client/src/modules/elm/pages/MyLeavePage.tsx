import { useState } from "react";
import { Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory, FaUserCheck } from "react-icons/fa";
import { useBalance, useLeaveRequests, useApplyLeaveRequest, useWithdrawLeaveRequest } from "./api/hooks";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";

export default function MyLeavePage() {
  const { data: balance, isPending: balancePending, error: balanceError } = useBalance();
  const { data: leaveRequests, isPending: leaveRequestsPending, error: leaveRequestsError } = useLeaveRequests();
  const applyMutation = useApplyLeaveRequest();
  const withdrawMutation = useWithdrawLeaveRequest();
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState(0);

  if (balanceError) return <Container size="xl"><ErrorState error={balanceError} /></Container>;
  if (leaveRequestsError) return <Container size="xl"><ErrorState error={leaveRequestsError} /></Container>;

  function apply() {
    applyMutation.mutate(
      { category, amount },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Applied",
            message: `Your leave request for ${amount} in ${category} has been applied.`,
          });
          setCategory("");
          setAmount(0);
        },
        onError: (e) => notifications.show({
          color: "red",
          title: "Could not apply",
          message: errorMessage(e),
        }),
      },
    );
  }

  function withdraw(id: number) {
    withdrawMutation.mutate(
      id,
      {
        onSuccess: () => notifications.show({
          color: "gray",
          title: "Withdrawn",
          message: "Your leave request has been withdrawn.",
        }),
        onError: (e) => notifications.show({
          color: "red",
          title: "Could not withdraw",
          message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave Requests"
        subtitle="Balance and list of your leave requests"
      />
      <Card padding="lg">
        <Stack>
          <Text fw={600}>Balance</Text>
          <Stack spacing="xs">
            {balance?.map((b) => (
              <Text key={b.category}>
                {b.category}: {b.amount}
              </Text>
            ))}
          </Stack>
        </Stack>
      </Card>
      <Card padding="lg">
        <Stack>
          <Text fw={600}>Apply for Leave</Text>
          <Group>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="Category"
            />
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              placeholder="Amount"
            />
            <Button onClick={apply}>Apply</Button>
          </Group>
        </Stack>
      </Card>
      <Card padding="lg">
        <Stack>
          <Text fw={600}>Leave Requests</Text>
          <Stack spacing="xs">
            {leaveRequests?.map((lr) => (
              <Stack key={lr.id}>
                <Text>{lr.category}: {lr.amount}</Text>
                <Text>{lr.applied_at}</Text>
                <StatusBadge status={lr.status} />
                {lr.status === "pending" && (
                  <Button onClick={() => withdraw(lr.id)}>Withdraw</Button>
                )}
              </Stack>
            ))}
          </Stack>
        </Stack>
      </Card>
    </Container>
  );
}
