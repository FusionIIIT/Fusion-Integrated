import { useState } from "react";
import { Alert, Card, Container, SimpleGrid, Stack, Text } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useOfficeActions, usePmsApplication } from "../api/hooks";
import { PmsActionForm } from "../components/PmsActionForm";
import { PmsApplicationSelect } from "../components/PmsApplicationSelect";

export default function OfficeActionsPage() {
  const { can } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const applicationId = selected ? Number(selected) : undefined;
  const detail = usePmsApplication(applicationId);
  const actions = useOfficeActions(applicationId);

  return (
    <Container size="xl">
      <PageHeader title="Office actions" subtitle="Record patent-office communications and manage response approval and submission." />
      <Card padding="lg"><PmsApplicationSelect value={selected} onChange={setSelected} /></Card>
      {detail.error && <Card mt="md"><ErrorState error={detail.error} /></Card>}
      {actions.error && <Card mt="md"><ErrorState error={actions.error} /></Card>}
      {detail.data && (
        <Stack mt="md" gap="md">
          <Card padding="md">
            <PageHeader title={`${detail.data.application_no} · ${detail.data.title}`}
              subtitle={`Application status: ${detail.data.status.replace(/_/g, " ")}`} />
          </Card>
          {can("pms.office_action.record") && (
            <PmsActionForm
              title="Record office action"
              path={() => `/applications/${detail.data!.id}/office-actions/`}
              fields={[
                { name: "action_type", label: "Action type", required: true },
                { name: "issue_date", label: "Issue date", type: "date", required: true },
                { name: "due_date", label: "Response due date", type: "date", required: true },
                { name: "details", label: "Communication details", type: "textarea", required: true },
                { name: "requires_applicant_review", label: "Applicant review is required", type: "checkbox", initialValue: true },
              ]}
              submitLabel="Record communication"
              successTitle="Office action recorded"
            />
          )}

          <PageHeader title="Recorded office actions" subtitle="Response actions are available according to the server-recorded stage and your IAM permission." />
          {actions.isPending ? <Text c="dimmed">Loading office actions…</Text> : (actions.data ?? []).length === 0 ? (
            <Alert color="gray" variant="light">No office actions are recorded for this application.</Alert>
          ) : (actions.data ?? []).map((item) => (
            <Card key={item.id} padding="lg">
              <Stack gap="md">
                <PageHeader title={`${item.action_type} · due ${item.due_date}`}
                  subtitle={item.details}
                  action={<StatusBadge status={item.status} />} />
                <SimpleGrid cols={{ base: 2, sm: 4 }}>
                  <Text size="sm">Issue date: {item.issue_date}</Text>
                  <Text size="sm">Applicant review: {item.requires_applicant_review ? "Required" : "Not required"}</Text>
                  <Text size="sm">Applicant approved: {item.applicant_approved ? "Yes" : "No"}</Text>
                  <Text size="sm">Extension: {item.extension_months || "None"}</Text>
                </SimpleGrid>
                {item.draft_response && <Text size="sm"><b>Draft response:</b> {item.draft_response}</Text>}
                {can("pms.office_action.respond") && item.status === "recorded" && (
                  <PmsActionForm
                    title="Draft response"
                    path={() => `/office-actions/${item.id}/draft-response/`}
                    fields={[{ name: "draft_response", label: "Draft", type: "textarea", required: true }]}
                    submitLabel="Save draft"
                  />
                )}
                {can("pms.office_action.review") && item.requires_applicant_review
                  && item.status === "awaiting_applicant_approval" && (
                    <PmsActionForm
                      title="Approve Attorney response"
                      path={() => `/office-actions/${item.id}/approve-response/`}
                      fields={[{ name: "approval", label: "I approve this response for submission", type: "checkbox", required: true }]}
                      transform={() => ({})}
                      submitLabel="Approve response"
                    />
                  )}
                {can("pms.office_action.respond")
                  && ["applicant_approved", "response_ready"].includes(item.status) && (
                    <PmsActionForm
                      title="Record response submission"
                      path={() => `/office-actions/${item.id}/submit-response/`}
                      fields={[{ name: "submission_details", label: "External submission details", type: "textarea", required: true }]}
                      submitLabel="Record submitted response"
                    />
                  )}
                {can("pms.office_action.respond") && item.status !== "response_submitted" && (
                  <PmsActionForm
                    title="Request an extension"
                    path={() => `/office-actions/${item.id}/extension/`}
                    fields={[{ name: "extension_months", label: "Extension (months, 1–12)", type: "number", required: true }]}
                    transform={(body) => ({ extension_months: Number(body.extension_months) })}
                    submitLabel="Request extension"
                    compact
                  />
                )}
              </Stack>
            </Card>
          ))}
        </Stack>
      )}
    </Container>
  );
}
