import { useState } from "react";
import { Button, Card, Container, Group, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CATEGORY_LABELS, useDecide, useInbox, type Decision, type LeaveApplication } from "../api";

export default function ApprovalsPage() {
  const { data, isPending, error } = useInbox();
  const decide = useDecide();
  const [remark, setRemark] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleDecision(id: number, decision: Decision) {
    decide.mutate({ id, decision, remark }, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Success",
          message: `Decision recorded for application ${id}.`,
        });
        setRemark("");
      },
      onError: (e) => {
        notifications.show({
          color: "red",
          title: "Error",
          message: errorMessage(e),
        });
      },
    });
  }

  function actionsFor(app: LeaveApplication): { label: string; decision: Decision; color: string }[] {
    switch (app.stage) {
      case "unit_head":
        if (app.category === "CL" || app.category === "RH") {
          return [
            { label: "Approve", decision: "approve", color: "blue" },
            { label: "Reject", decision: "reject", color: "red" },
          ];
        }
        return [
          { label: "Recommend", decision: "recommended", color: "orange" },
          { label: "Not recommended", decision: "not_recommended", color: "gray" },
        ];
      case "establishment":
        return [{ label: "Verify", decision: "verify", color: "indigo" }];
      case "sanction":
        return [
          { label: "Approve", decision: "approve", color: "blue" },
          { label: "Reject", decision: "reject", color: "red" },
        ];
      default:
        return [];
    }
  };

  const rows = (data ?? []).filter((a) => a.stage !== "substitute");

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Approvals"
        subtitle="Requests waiting for your decision"
      />
      <TextInput
        label="Remark (optional)"
        value={remark}
        onChange={(e) => setRemark(e.currentTarget.value)}
        mb="md"
      />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={rows}
          columns={[
            { key: "applicant", header: "Applicant", render: (r) => r.user_id },
            { key: "category", header: "Category", render: (r) => {
              const categoryLabel = r.kind === "cancellation" ? `${r.category.toUpperCase()} (cancellation)` : CATEGORY_LABELS[r.category];
              return categoryLabel;
            }},
            { key: "start_date", header: "Dates", render: (r) => `${r.start_date} to ${r.end_date}` },
            { key: "days", header: "Days", render: (r) => r.days },
            { key: "purpose", header: "Purpose", render: (r) => r.purpose || "—" },
            { key: "stage", header: "Stage", render: (r) => r.stage.replace(/_/g, " ") },
            { key: "unit_head_recommendation", header: "Unit Head recommendation", render: (r) => r.unit_head_recommendation || "—" },
            { key: "actions", header: "Actions", render: (r) => (
              <Group gap="xs">
                {actionsFor(r).map((action) => (
                  <Button
                    key={action.decision}
                    color={action.color}
                    loading={decide.isPending}
                    size="xs"
                    onClick={() => handleDecision(r.id, action.decision)}
                  >
                    {action.label}
                  </Button>
                ))}
              </Group>
            )},
          ]}
          loading={isPending}
          rowKey={(r: LeaveApplication) => r.id}
          empty={{ title: "No pending approvals", description: "Requests assigned to you appear here." }}
        />
      </Card>
    </Container>
  );
}
