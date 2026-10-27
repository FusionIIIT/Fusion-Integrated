import { Alert, Button, Container, Group, Paper, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAction, useAssignedTasks, useResumptions, useReviewResumption } from "../api/hooks";
import { StateBadge } from "../components/StateBadge";

export default function TasksPage() {
  const tasks = useAssignedTasks();
  const resumptions = useResumptions();
  const action = useAction();
  const review = useReviewResumption();
  if (tasks.error) return <Container size="lg"><ErrorState error={tasks.error} /></Container>;
  if (resumptions.error) return <Container size="lg"><ErrorState error={resumptions.error} /></Container>;
  const rows = tasks.data ?? [];
  const resumeRows = (resumptions.data ?? []).filter((row) => row.state === "resumption_review_pending");
  return (
    <Container size="lg">
      <PageHeader title="Assigned Leave Tasks" subtitle="Tasks assigned to your active IAM role." />
      {rows.length === 0 && resumeRows.length === 0
        ? <Alert color="gray">There are no tasks assigned to you.</Alert>
        : <Stack>
          {rows.map((row) => {
            const substitute = row.status.includes("substitute_response");
            const unitHead = row.status.includes("unit_head_review");
            const establishment = row.status.includes("establishment");
            const director = row.status.includes("director_self");
            const final = row.status.includes("final_sanction");
            const cancelUnit = row.status === "cancellation_pending_unit_head_review";
            const cancelFinal = row.status === "cancellation_pending_final_decision";
            const canReview = unitHead || cancelUnit;
            const canRoute = establishment;
            const canDecide = final || director || cancelFinal;
            return <Paper key={row.id} withBorder p="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4}>
                  <Text fw={600}>Request {row.id} · {row.leave_type}</Text>
                  <Text size="sm">{row.start_date} – {row.end_date} · {row.requested_days} days</Text>
                  <Text size="sm" c="dimmed">{row.purpose}</Text>
                  <StateBadge status={row.status} />
                </Stack>
                <Group>
                  {substitute && <>
                    <Button loading={action.isPending} onClick={() => action.mutate({
                      id: row.id, event: "accept_substitute",
                    }, { onError: (error) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(error) }) })}>Accept</Button>
                    <Button color="orange" variant="light" loading={action.isPending}
                      onClick={() => action.mutate({ id: row.id, event: "decline_substitute" }, {
                        onError: (error) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(error) }),
                      })}>Decline</Button>
                  </>}
                  {canReview && row.request_kind === "cancellation" && <>
                    <Button loading={action.isPending} onClick={() => action.mutate({
                      id: row.id, event: "unit_head_cancel", outcome: "approve",
                    }, { onError: (error) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(error) }) })}>Approve cancellation</Button>
                    <Button color="red" variant="light" loading={action.isPending}
                      onClick={() => action.mutate({ id: row.id, event: "unit_head_cancel", outcome: "reject" })}>Reject cancellation</Button>
                  </>}
                  {canReview && row.request_kind !== "cancellation" && (
                    row.leave_type === "CL" || row.leave_type === "RH" ? <>
                      <Button loading={action.isPending} onClick={() => action.mutate({
                        id: row.id, event: "unit_head_decision", outcome: "approve",
                      }, { onError: (error) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(error) }) })}>Approve</Button>
                      <Button color="red" variant="light" loading={action.isPending}
                        onClick={() => action.mutate({ id: row.id, event: "unit_head_decision", outcome: "reject" })}>Reject</Button>
                    </> : <>
                      <Button loading={action.isPending} onClick={() => action.mutate({
                        id: row.id, event: "unit_head_decision", outcome: "recommended", note: "Recommended",
                      }, { onError: (error) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(error) }) })}>Recommend</Button>
                      <Button color="orange" variant="light" loading={action.isPending}
                        onClick={() => action.mutate({ id: row.id, event: "unit_head_decision",
                          outcome: "not_recommended", note: "Not Recommended" })}>Not recommended</Button>
                    </>
                  )}
                  {canRoute && <Button loading={action.isPending} onClick={() => action.mutate({
                    id: row.id, event: "route",
                  }, { onError: (error) => notifications.show({ color: "red", title: "Routing failed", message: errorMessage(error) }) })}>Route</Button>}
                  {canDecide && <>
                    <Button loading={action.isPending} onClick={() => action.mutate({
                      id: row.id, event: director ? "director_sanction" : "sanction", outcome: "approve",
                    }, { onError: (error) => notifications.show({ color: "red", title: "Decision failed", message: errorMessage(error) }) })}>Approve</Button>
                    <Button color="red" variant="light" loading={action.isPending}
                      onClick={() => action.mutate({ id: row.id,
                        event: director ? "director_sanction" : "sanction", outcome: "reject" })}>Reject</Button>
                  </>}
                </Group>
              </Group>
            </Paper>;
          })}
          {resumeRows.map((row) => <Paper key={`resume-${row.id}`} withBorder p="md">
            <Group justify="space-between">
              <Stack gap={4}><Text fw={600}>Resumption review · Request {row.application_id}</Text>
                <Text size="sm">Actual return: {row.actual_resumption_date}</Text>
                <StateBadge status={row.state} /></Stack>
              <Button loading={review.isPending} onClick={() => review.mutate(row.id, {
                onSuccess: () => notifications.show({ title: "Resumption reviewed", message: "The local leave record was updated." }),
                onError: (error) => notifications.show({ color: "red", title: "Review failed", message: errorMessage(error) }),
              })}>Review</Button>
            </Group>
          </Paper>)}
        </Stack>}
    </Container>
  );
}
