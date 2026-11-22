import { useState } from "react";
import { Alert, Card, Container, Group, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePmsApplication } from "../api/hooks";
import { PmsActionForm } from "../components/PmsActionForm";
import { PmsApplicationSelect } from "../components/PmsApplicationSelect";

export default function FilingsPage() {
  const { can, session } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = usePmsApplication(selected ? Number(selected) : undefined);

  return (
    <Container size="xl">
      <PageHeader title="Attorney workspace" subtitle="Assignment response, patentability advice, and external filing records." />
      <Card padding="lg"><PmsApplicationSelect value={selected} onChange={setSelected} /></Card>
      {detail.error && <Card mt="md"><ErrorState error={detail.error} /></Card>}
      {detail.isPending && selected && <Text c="dimmed" mt="md">Loading application…</Text>}
      {detail.data && (
        <Stack mt="md" gap="md">
          <Card padding="md">
            <PageHeader title={`${detail.data.application_no} · ${detail.data.title}`}
              subtitle={`Budget: ${detail.data.budget?.status ?? "not recorded"} · Agreements: ${detail.data.coinventors.every((c) => c.agreement_signed) ? "complete" : "pending"}`}
              action={<StatusBadge status={detail.data.status} />} />
            <Group gap="md">
              <Link to="../office-actions">Open office-action workspace</Link>
              <Link to="../licensing">Open licensing requests</Link>
            </Group>
          </Card>

          {can("pms.prior_art.search") && (
            <Alert color="yellow" variant="light">
              Prior-art search is not available here because the current backend search service returns sample results rather than querying connected patent or publication sources. No results are presented as real.
            </Alert>
          )}

          {can("pms.attorney.respond_assignment") && detail.data.attorney_assignments
            .filter((assignment) => assignment.attorney_user_id === session?.user.id
              && assignment.is_active && assignment.status === "offered")
            .map((assignment) => (
              <Group key={assignment.id} grow align="flex-start">
                <PmsActionForm
                  title="Accept attorney assignment"
                  path={() => `/attorney-assignments/${assignment.id}/respond/`}
                  fields={[{ name: "accept", label: "Confirm acceptance", type: "checkbox", initialValue: true }]}
                  transform={() => ({ accept: true })}
                  submitLabel="Accept assignment"
                />
                <PmsActionForm
                  title="Decline attorney assignment"
                  path={() => `/attorney-assignments/${assignment.id}/respond/`}
                  fields={[{ name: "decline_reason", label: "Reason", type: "textarea", required: true }]}
                  transform={(body) => ({ accept: false, decline_reason: body.decline_reason })}
                  submitLabel="Decline"
                />
              </Group>
            ))}

          {can("pms.patentability.assess") && (
            <PmsActionForm
              title="Patentability assessment"
              path={() => `/applications/${detail.data!.id}/patentability/`}
              fields={[
                { name: "recommendation", label: "Recommendation", type: "select", required: true, options: [
                  { value: "File Patent", label: "File Patent" },
                  { value: "Do Not File", label: "Do Not File" },
                  { value: "Needs Amendment", label: "Needs Amendment" },
                ] },
                { name: "opinion_text", label: "Opinion", type: "textarea", required: true },
                { name: "novelty_score", label: "Novelty score (0–100)", type: "number", initialValue: "0" },
                { name: "non_obviousness_score", label: "Non-obviousness score (0–100)", type: "number", initialValue: "0" },
                { name: "utility_score", label: "Utility score (0–100)", type: "number", initialValue: "0" },
              ]}
              transform={(body) => ({
                ...body,
                novelty_score: Number(body.novelty_score),
                non_obviousness_score: Number(body.non_obviousness_score),
                utility_score: Number(body.utility_score),
              })}
              successTitle="Assessment recorded"
              submitLabel="Record opinion"
            />
          )}

          {can("pms.advice.record") && (
            <PmsActionForm
              title="Record patent legal advice"
              path={() => `/applications/${detail.data!.id}/legal-advice/`}
              fields={[
                { name: "stage", label: "Lifecycle stage", required: true },
                { name: "advice_text", label: "Advice", type: "textarea", required: true },
              ]}
              submitLabel="Record advice"
            />
          )}

          {can("pms.filing.record") && (
            <>
              <Alert color="blue" variant="light">
                Filing prerequisites are checked on the server when you submit the external filing record. PMS does not submit to the patent office.
              </Alert>
              <PmsActionForm
                title="Record external filing"
                path={() => `/applications/${detail.data!.id}/filing/`}
                fields={[
                  { name: "external_filing_id", label: "External filing ID", required: true },
                  { name: "external_filing_date", label: "Filing date", type: "date", required: true },
                  { name: "filing_confirmation", label: "Filing confirmation", type: "textarea", required: true },
                  { name: "is_international", label: "International filing", type: "checkbox" },
                  { name: "international_justification", label: "International justification", type: "textarea" },
                ]}
                submitLabel="Record filing"
                successTitle="Filing recorded"
                successMessage="PMS stored the filing confirmation returned from the external patent office."
              />
              <PmsActionForm
                title="Record patent grant"
                path={() => `/applications/${detail.data!.id}/grant/`}
                fields={[
                  { name: "patent_number", label: "Patent number", required: true },
                  { name: "grant_date", label: "Grant date", type: "date", required: true },
                ]}
                submitLabel="Record grant"
                successTitle="Grant recorded"
                successMessage="PMS stored the grant and created a maintenance cycle only when a schedule is configured."
              />
            </>
          )}
        </Stack>
      )}
    </Container>
  );
}
