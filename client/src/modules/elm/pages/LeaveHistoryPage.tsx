import { Container, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { LeaveHistory } from "../components/LeaveHistory";
import {
  useLeaveRequests, useWithdrawLeave, useWithdrawLeaveCase,
} from "../hooks/useLeaveManagement";
import { useElmRole } from "../hooks/useRole";

export default function LeaveHistoryPage() {
  const requests = useLeaveRequests();
  const role = useElmRole();
  const withdraw = useWithdrawLeave();
  const withdrawCase = useWithdrawLeaveCase();
  if (requests.error) {
    return <Container size="xl"><ErrorState error={requests.error} /></Container>;
  }
  return (
    <Container size="xl">
      <PageHeader title="Leave History" subtitle="Your submitted and completed leave requests" />
      {requests.isPending
        ? <Text c="dimmed">Loading leave history…</Text>
        : <LeaveHistory
          requests={requests.data ?? []}
          userId={role.userId}
          canWithdraw={role.canWithdraw}
          onWithdraw={(request) => withdraw.mutate(request.id)}
          onCase={() => undefined}
          onReplaceSubstitute={() => undefined}
          onWithdrawCase={(item) => withdrawCase.mutate(item.id)}
          onReplaceCaseSubstitute={() => undefined}
        />}
    </Container>
  );
}