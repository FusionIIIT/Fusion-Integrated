TITLE: Rewrite the Approvals page again after review of 013 found 16 TypeScript errors
FORMAT: whole
EDIT: client/src/modules/leave/pages/ApprovalsPage.tsx
READ: client/src/modules/leave/api.ts client/src/ui/components/DataTable.tsx client/src/modules/placement/pages/MyApplicationsPage.tsx
LIMIT: 1500
POST: none
---
Review of ApprovalsPage.tsx from task 013 (tsc reports 16 errors): it calls useDecide.mutate on the hook function itself, passes a render function as DataTable children (DataTable has no children; each column has its own render), declares columns without render, reads data.results although the hook returns an array, uses Text without importing it, and passes `clearable` to TextInput (no such prop). Keep its actionsFor helper exactly as it is (it is correct) and rewrite the whole file with this structure, following the DataTable usage in placement's MyApplicationsPage.tsx (read-only):

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

  const rows = (data ?? []).filter((a) => a.stage !== "substitute");

  function handleDecision(id: number, decision: Decision) {
    decide.mutate({ id, decision, remark }, { onSuccess: ... notification + setRemark(""), onError: ... errorMessage(e) });
  }

  function actionsFor(app: LeaveApplication) { ... keep the existing switch ... }

  return (
    <Container size="xl">
      <PageHeader title="Leave Approvals" subtitle="Requests waiting for your decision" />
      <TextInput label="Remark (optional)" value={remark} onChange={(e) => setRemark(e.currentTarget.value)} mb="md" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[ ...eight columns, each { key, header, render: (r) => ... } ... ]}
          empty={{ title: "No pending approvals", description: "Requests assigned to you appear here." }}
        />
      </Card>
    </Container>
  );
}

The eight columns: Applicant (r.user_id), Category (CATEGORY_LABELS[r.category] plus " (cancellation)" when r.kind === "cancellation"), Dates (`${r.start_date} to ${r.end_date}`), Days (r.days), Purpose (r.purpose), Stage (r.stage.replace(/_/g, " ")), Unit Head recommendation (r.unit_head_recommendation || "-"), Actions (a Group of size="xs" Buttons from actionsFor(r), each with key={a.decision}, color={a.color}, loading={decide.isPending}, onClick={() => handleDecision(r.id, a.decision)}).
Every notifications.show call needs color, title AND message. Write the whole file. Do not ask for more files.
