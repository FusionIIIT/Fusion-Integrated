import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useParams } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAppAction, useApplication } from "../api";

type Field = { name: string; label: string; kind: "text" | "textarea" | "number" | "select"; options?: string[] };
type Spec = { action: string; title: string; fields: Field[] };

const PRE_FILING = ["draft", "submitted", "under_review", "needs_revision", "resubmitted",
  "approved", "rejected", "remanded_for_amendment"];

export default function DetailPage() {
  const { id } = useParams();
  const appId = Number(id);
  const { data: app, error, isPending } = useApplication(appId);
  const act = useAppAction(appId);
  const { session } = useAuth();
  const [spec, setSpec] = useState<Spec | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  if (isPending || !app) return null;

  const me = session?.user.id;
  const can = (p: string) => session?.permissions.includes(p) ?? false;
  const isApplicant = app.applicant_user_id === me;
  const isDirector = app.director_user_id === me;
  const isAttorney = app.attorney_user_id === me;

  function run(action: string, body: Record<string, unknown> = {}, title = "Saved") {
    act.mutate({ action, body }, {
      onSuccess: () => { setSpec(null); setValues({}); notifications.show({ color: "green", title, message: "Recorded." }); },
      onError: (e) => notifications.show({ color: "red", title: "Could not save", message: errorMessage(e) }),
    });
  }

  function submitSpec() {
    if (!spec) return;
    const body: Record<string, unknown> = {};
    for (const f of spec.fields) if (values[f.name] !== undefined && values[f.name] !== "") body[f.name] = values[f.name];
    run(spec.action, body, spec.title);
  }

  const actions: { label: string; onClick: () => void; color?: string }[] = [];
  const form = (label: string, s: Spec) => actions.push({ label, onClick: () => { setSpec(s); setValues({}); } });
  const direct = (label: string, action: string, body: Record<string, unknown>, color?: string) =>
    actions.push({ label, color, onClick: () => run(action, body, label) });

  if (isApplicant && app.status === "draft" && can("patent_management.application.submit"))
    direct("Submit application", "submit", {});
  if (isApplicant && can("patent_management.application.revise") && ["needs_revision", "rejected", "remanded_for_amendment"].includes(app.status))
    form("Revise and resubmit", { action: "revise", title: "Revise and resubmit",
      fields: [{ name: "response", label: "How the revision addresses the feedback", kind: "textarea" }] });
  if (isApplicant && can("patent_management.application.appeal") && app.status === "rejected")
    form("Appeal", { action: "appeal", title: "File an appeal",
      fields: [{ name: "grounds", label: "Grounds", kind: "textarea" }] });
  if (isApplicant && can("patent_management.application.withdraw") && PRE_FILING.includes(app.status))
    form("Withdraw", { action: "withdraw", title: "Withdraw application",
      fields: [{ name: "reason", label: "Reason", kind: "textarea" }] });

  if (can("patent_management.route.manage") && ["submitted", "resubmitted"].includes(app.status))
    form("Assign director", { action: "assign-director", title: "Assign director",
      fields: [{ name: "director_user_id", label: "Director user id", kind: "number" }] });
  if (can("patent_management.route.manage") && app.status === "approved" && !app.attorney_user_id)
    form("Assign attorney", { action: "assign-attorney", title: "Assign attorney",
      fields: [{ name: "attorney_user_id", label: "Attorney user id", kind: "number" }] });

  if (isDirector && can("patent_management.review.decide") && app.status === "under_review")
    form("Record review decision", { action: "review", title: "Review decision", fields: [
      { name: "decision", label: "Decision", kind: "select", options: ["approve", "reject", "needs_revision"] },
      { name: "justification", label: "Justification (min 50 characters)", kind: "textarea" }] });
  if (isDirector && can("patent_management.appeal.decide") && app.status === "appeal_submitted")
    form("Decide appeal", { action: "appeal-decision", title: "Appeal decision", fields: [
      { name: "outcome", label: "Outcome", kind: "select", options: ["uphold", "remand", "modify"] },
      { name: "reasoning", label: "Reasoning", kind: "textarea" }] });
  if (isDirector && can("patent_management.budget.decide") && app.budget_status === "pending") {
    direct("Approve budget", "budget-decision", { decision: "approve" });
    direct("Reject budget", "budget-decision", { decision: "reject" }, "red");
  }

  if (isAttorney && app.attorney_status === "offered") {
    direct("Accept assignment", "attorney-response", { accept: true });
    direct("Decline assignment", "attorney-response", { accept: false }, "red");
  }
  if (isAttorney && app.attorney_status === "accepted") {
    form("Record opinion", { action: "opinion", title: "Patentability opinion", fields: [
      { name: "recommendation", label: "Recommendation", kind: "select", options: ["file_patent", "do_not_file", "needs_amendment"] },
      { name: "text", label: "Opinion", kind: "textarea" }] });
    if (app.status === "approved")
      form("Record budget", { action: "budget", title: "Record budget", fields: [
        { name: "filing_fee", label: "Filing fee", kind: "number" },
        { name: "attorney_fee", label: "Attorney fee", kind: "number" },
        { name: "admin_cost", label: "Administrative cost", kind: "number" }] });
    if (app.status === "approved" && app.budget_status === "approved")
      form("Record filing", { action: "filing", title: "External filing", fields: [
        { name: "external_filing_id", label: "External filing ID", kind: "text" },
        { name: "filing_date", label: "Filing date (YYYY-MM-DD)", kind: "text" }] });
  }

  return (
    <Container size="xl">
      <PageHeader title={app.title} subtitle={app.application_no}
        action={<Badge size="lg" variant="light">{app.status_label}</Badge>} />
      <Stack gap="lg">
        {actions.length > 0 && (
          <Card padding="md">
            <Text fw={600} size="sm" mb="xs">Next actions</Text>
            <Group gap="xs">
              {actions.map((a) => (
                <Button key={a.label} size="xs" variant="light" color={a.color} loading={act.isPending} onClick={a.onClick}>
                  {a.label}
                </Button>
              ))}
            </Group>
          </Card>
        )}

        {spec && (
          <Card padding="lg">
            <Text fw={600} mb="sm">{spec.title}</Text>
            <Stack gap="sm">
              {spec.fields.map((f) =>
                f.kind === "select" ? (
                  <Select key={f.name} label={f.label} data={f.options ?? []}
                    value={(values[f.name] as string) ?? null}
                    onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))} />
                ) : f.kind === "number" ? (
                  <NumberInput key={f.name} label={f.label} value={(values[f.name] as number) ?? ""}
                    onChange={(v) => setValues((s) => ({ ...s, [f.name]: v === "" ? undefined : Number(v) }))} />
                ) : f.kind === "textarea" ? (
                  <Textarea key={f.name} label={f.label} autosize minRows={3}
                    value={(values[f.name] as string) ?? ""}
                    onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.currentTarget.value }))} />
                ) : (
                  <TextInput key={f.name} label={f.label} value={(values[f.name] as string) ?? ""}
                    onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.currentTarget.value }))} />
                ),
              )}
              <Group justify="flex-end">
                <Button variant="subtle" onClick={() => setSpec(null)}>Cancel</Button>
                <Button loading={act.isPending} onClick={submitSpec}>Save</Button>
              </Group>
            </Stack>
          </Card>
        )}

        <Card padding="lg">
          <Text fw={600} mb="xs">Proposal</Text>
          <Text size="sm" fw={500}>Abstract</Text>
          <Text size="sm" mb="sm" style={{ whiteSpace: "pre-wrap" }}>{app.abstract || "—"}</Text>
          <Text size="sm" fw={500}>Description</Text>
          <Text size="sm" mb="sm" style={{ whiteSpace: "pre-wrap" }}>{app.description || "—"}</Text>
          <Text size="sm" fw={500}>Claims</Text>
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{app.claims || "—"}</Text>
        </Card>

        <Card padding="lg">
          <Text fw={600} mb="xs">History</Text>
          <Stack gap={6}>
            {app.events.length === 0 && <Text size="sm" c="dimmed">No events yet.</Text>}
            {app.events.map((e) => (
              <Text key={e.id} size="sm">
                <Text span c="dimmed">{new Date(e.created_at).toLocaleString()}</Text>
                {` · ${e.action}`}{e.to_state ? ` → ${e.to_state}` : ""}{e.detail ? ` — ${e.detail}` : ""}
              </Text>
            ))}
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
