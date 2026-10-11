import { useState } from "react";
import {
  Alert, Card, Container, Grid, Group, SimpleGrid, Stack, Text, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { LeaveCaseForm } from "../components/LeaveCaseForm";
import { LeaveHistory } from "../components/LeaveHistory";
import { LeaveRequestForm } from "../components/LeaveRequestForm";
import {
  useCreateLeave, useCreateLeaveCase, useElmSummary, useLeaveRequests,
  useReplaceCaseSubstitute, useReplaceSubstitute, useWithdrawLeave,
  useWithdrawLeaveCase,
} from "../hooks/useLeaveManagement";
import { useElmRole } from "../hooks/useRole";
import type { LeaveRequest } from "../types";

export default function LeaveRequestsPage() {
  const summary = useElmSummary();
  const requests = useLeaveRequests();
  const role = useElmRole();
  const create = useCreateLeave();
  const withdraw = useWithdrawLeave();
  const createCase = useCreateLeaveCase();
  const replace = useReplaceSubstitute();
  const replaceCase = useReplaceCaseSubstitute();
  const withdrawCase = useWithdrawLeaveCase();
  const [caseRequest, setCaseRequest] = useState<LeaveRequest | null>(null);
  const [caseKind, setCaseKind] = useState<
    "cancellation" | "extension" | "resumption" | null>(null);
  const [formKey, setFormKey] = useState(0);
  const [error, setError] = useState("");

  if (summary.error || requests.error) {
    return <Container size="xl"><ErrorState error={summary.error ?? requests.error} /></Container>;
  }

  const startCase = (
    request: LeaveRequest, kind: "cancellation" | "extension" | "resumption",
  ) => {
    setCaseRequest(request);
    setCaseKind(kind);
  };
  const notifyError = (title: string, reason: unknown) => {
    notifications.show({ color: "red", title, message: errorMessage(reason) });
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Employee Leave Management"
        subtitle="Apply for leave, track approvals and review your leave account"
      />
      <Stack>
        {error && <Alert color="red" title="Action could not be completed">{error}</Alert>}
        <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }}>
          {(summary.data?.balances ?? []).map((balance) => (
            <Card key={`${balance.category}-${balance.year}`} withBorder padding="sm">
              <Text size="xs" c="dimmed">{balance.category} · {balance.year}</Text>
              <Text fw={700} size="xl">{balance.balance}</Text>
              <Text size="xs" c="dimmed">available days</Text>
            </Card>
          ))}
        </SimpleGrid>
        <Grid align="flex-start">
          {role.isEmployee && (
            <Grid.Col span={{ base: 12, lg: 5 }}>
              <Card withBorder padding="lg">
                <Title order={4} mb="md">New leave application</Title>
                <LeaveRequestForm
                  key={formKey}
                  loading={create.isPending}
                  onSubmit={(input) => create.mutate(input, {
                    onSuccess: () => {
                      setFormKey((key) => key + 1);
                      setError("");
                      notifications.show({
                        color: "green", title: "Application submitted",
                        message: "Your leave request has entered the approval process.",
                      });
                    },
                    onError: (reason) => notifyError("Could not submit application", reason),
                  })}
                />
              </Card>
            </Grid.Col>
          )}
          <Grid.Col span={{ base: 12, lg: role.isEmployee ? 7 : 12 }}>
            <Card withBorder padding="lg">
              <Group justify="space-between" mb="md">
                <Title order={4}>My leave requests</Title>
                {summary.data && (
                  <Text size="sm" c="dimmed">
                    {summary.data.pending_requests} pending
                  </Text>
                )}
              </Group>
              {requests.isPending
                ? <Text c="dimmed">Loading leave requests…</Text>
                : <LeaveHistory
                  requests={requests.data ?? []}
                  userId={role.userId}
                  canWithdraw={role.canWithdraw}
                  onWithdraw={(request) => withdraw.mutate(request.id, {
                    onSuccess: () => notifications.show({
                      color: "green", title: "Request withdrawn",
                      message: "All further approval processing has stopped.",
                    }),
                    onError: (reason) => notifyError("Could not withdraw request", reason),
                  })}
                  onCase={startCase}
                  onReplaceSubstitute={(request) => {
                    const raw = window.prompt("Enter the replacement employee ID");
                    if (!raw) return;
                    const id = Number(raw);
                    if (!Number.isInteger(id) || id < 1) {
                      setError("Enter a valid employee ID for the replacement substitute.");
                      return;
                    }
                    replace.mutate(
                      { id: request.id, substitute_user_id: id },
                      {
                        onSuccess: () => setError(""),
                        onError: (reason) => notifyError("Could not replace substitute", reason),
                      },
                    );
                  }}
                  onWithdrawCase={(item) => withdrawCase.mutate(item.id)}
                  onReplaceCaseSubstitute={(item) => {
                    const raw = window.prompt("Enter the replacement employee ID");
                    if (!raw) return;
                    const id = Number(raw);
                    if (!Number.isInteger(id) || id < 1) {
                      setError("Enter a valid employee ID for the replacement substitute.");
                      return;
                    }
                    replaceCase.mutate({ id: item.id, substitute_user_id: id }, {
                      onSuccess: () => setError(""),
                      onError: (reason) => notifyError(
                        "Could not replace substitute", reason),
                    });
                  }}
                />}
            </Card>
          </Grid.Col>
        </Grid>
      </Stack>
      <LeaveCaseForm
        request={caseRequest}
        kind={caseKind}
        loading={createCase.isPending}
        onClose={() => { setCaseRequest(null); setCaseKind(null); }}
        onSubmit={(body) => {
          if (!caseRequest) return;
          createCase.mutate({ id: caseRequest.id, body }, {
            onSuccess: () => {
              setCaseRequest(null);
              setCaseKind(null);
              notifications.show({
                color: "green", title: "Request submitted",
                message: "The request has been routed for review.",
              });
            },
            onError: (reason) => notifyError("Could not submit leave action", reason),
          });
        }}
      />
    </Container>
  );
}