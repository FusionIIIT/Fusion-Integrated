import { Alert, Badge, Button, Card, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApprovalDecision, useApprovalQueue } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

function actionsFor(app: LeaveApplication) {
  const stage = app.workflow_stage ?? (
    app.status === "awaiting_unit_head_review" ? "unit_head"
      : app.status === "awaiting_establishment_routing" ? "establishment"
      : "final_authority"
  );
  if (stage === "unit_head") {
    return ["CL", "RH"].includes(app.leave_category_code)
      ? ["approved", "rejected"]
      : ["recommended", "not_recommended"];
  }
  if (stage === "establishment") return ["routed"];
  return ["approved", "rejected"];
}

export default function ApprovalQueuePage() {
  const query = useApprovalQueue();
  const decision = useApprovalDecision();
  const [comments, setComments] = useState("");
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  const items = query.data ?? [];

  const submit = (app: LeaveApplication, outcome: string) => {
    decision.mutate({ pk: app.pk, workflow_kind: app.workflow_kind ?? "leave", outcome: outcome as "approved", comments });
  };

  return (
    <Container size="lg">
      <PageHeader title="Leave Approvals" subtitle="Items assigned to your active configured role" />
      {decision.error && <Alert color="red">{String(decision.error)}</Alert>}
      {items.length === 0 ? (
        <Alert color="gray">No leave requests are waiting for your active role.</Alert>
      ) : (
        <Stack>
          <Textarea label="Decision comments" value={comments} onChange={(event) => setComments(event.currentTarget.value)} />
          {items.map((app) => (
            <Card withBorder key={app.pk}>
              <Group justify="space-between" mb="sm">
                <Text fw={600}>ELM-{app.pk} · {app.leave_category_label}{app.workflow_kind === "cancellation" ? " · Cancellation" : ""}</Text>
                <Badge>{app.status.replaceAll("_", " ")}</Badge>
              </Group>
              <Text>Applicant: {app.employee_user_id}</Text>
              <Text>Period: {app.requested_start} – {app.requested_end} · {app.day_part.replaceAll("_", " ")}</Text>
              <Text>Purpose: {app.purpose_reason || "Not specified"}</Text>
              <Group mt="md">
                {actionsFor(app).map((outcome) => (
                  <Button key={outcome} variant={outcome === "rejected" || outcome === "not_recommended" ? "light" : "filled"}
                    color={outcome === "rejected" || outcome === "not_recommended" ? "red" : "blue"}
                    loading={decision.isPending}
                    onClick={() => submit(app, outcome)}>
                    {outcome.replaceAll("_", " ")}
                  </Button>
                ))}
              </Group>
            </Card>
          ))}
        </Stack>
      )}
    </Container>
  );
}
