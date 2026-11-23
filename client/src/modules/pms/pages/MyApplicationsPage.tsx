import { useState } from "react";
import { Alert, Button, Card, Container, Grid, Group, SimpleGrid, Stack, Text } from "@mantine/core";
import { FaArrowRight, FaEye } from "react-icons/fa";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePmsApplication, usePmsApplications } from "../api/hooks";
import type { PatentApplication } from "../api/types";
import { PmsActionForm } from "../components/PmsActionForm";

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return <div><Text size="xs" c="dimmed">{label}</Text><Text fw={500}>{value || "—"}</Text></div>;
}

export default function MyApplicationsPage() {
  const { can } = useAuth();
  const [selectedId, setSelectedId] = useState<number>();
  const list = usePmsApplications();
  const detail = usePmsApplication(selectedId);

  if (list.error) return <Container size="xl"><ErrorState error={list.error} /></Container>;

  const columns: Column<PatentApplication>[] = [
    { key: "application_no", header: "Application" },
    { key: "title", header: "Title" },
    { key: "domain", header: "Domain" },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    {
      key: "open", header: "", align: "right",
      render: (row) => (
        <Button size="xs" variant="light" leftSection={<FaEye size={12} />}
          onClick={() => setSelectedId(row.id)}>
          Track
        </Button>
      ),
    },
  ];

  return (
    <Container size="xl">
      <PageHeader title="My Applications" subtitle="Track your patent applications and take available actions." />
      <Card padding="lg">
        <DataTable
          rows={list.data ?? []} columns={columns} rowKey={(row) => row.id}
          loading={list.isPending}
          empty={{ title: "No applications yet", description: "Submitted applications will appear here." }}
          minWidth={800}
        />
      </Card>

      {selectedId != null && (
        <Card padding="lg" mt="md">
          {detail.error ? <ErrorState error={detail.error} /> : detail.isPending ? (
            <Text c="dimmed">Loading application…</Text>
          ) : detail.data && (
            <Stack gap="md">
              <PageHeader
                title={detail.data.application_no}
                subtitle={detail.data.title}
                action={<StatusBadge status={detail.data.status} />}
              />
              <SimpleGrid cols={{ base: 2, sm: 4 }}>
                <Fact label="Domain" value={detail.data.domain} />
                <Fact label="Jurisdiction" value={detail.data.jurisdiction} />
                <Fact label="Director" value={detail.data.assigned_director_user_id} />
                <Fact label="Attorney" value={detail.data.assigned_attorney_user_id} />
                <Fact label="Review deadline" value={detail.data.review_deadline} />
                <Fact label="Revision deadline" value={detail.data.revision_deadline} />
                <Fact label="Filed on" value={detail.data.external_filing_date} />
                <Fact label="Patent number" value={detail.data.patent_number} />
              </SimpleGrid>
              <Grid>
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Text size="sm" fw={600}>Abstract</Text>
                  <Text size="sm" c="dimmed" mt={4}>{detail.data.abstract}</Text>
                </Grid.Col>
                <Grid.Col span={{ base: 12, md: 6 }}>
                  <Text size="sm" fw={600}>Latest review feedback</Text>
                  <Text size="sm" c="dimmed" mt={4}>
                    {detail.data.director_reviews.slice(-1)[0]?.feedback || "No feedback recorded."}
                  </Text>
                </Grid.Col>
              </Grid>
              <Group gap="xs">
                {detail.data.documents.map((doc) => (
                  <Text key={doc.id} size="xs" c="dimmed">
                    {doc.title} · v{doc.version}{doc.is_current ? " · current" : ""}
                  </Text>
                ))}
              </Group>
              <Group gap="md">
                <Link to="../office-actions">Open office actions</Link>
                <Link to="../licensing">Open licensing requests</Link>
                <Link to="../maintenance">Open maintenance</Link>
              </Group>
              {can("pms.document.manage") && (
                <>
                  <Alert color="blue" variant="light">
                    PMS currently stores document metadata and an external file URL. It does not accept or scan a binary file through this API.
                  </Alert>
                  <PmsActionForm
                    title="Record document version metadata"
                    path={() => `/applications/${detail.data!.id}/documents/`}
                    fields={[
                      { name: "doc_type", label: "Document type", required: true },
                      { name: "title", label: "Document title", required: true },
                      { name: "filename", label: "Filename", required: true },
                      { name: "file_size_bytes", label: "File size in bytes (under 50 MB)", type: "number", min: 0, max: 52_428_799, required: true },
                      { name: "sensitivity", label: "Sensitivity classification", initialValue: "confidential" },
                      { name: "file_url", label: "Existing storage URL" },
                    ]}
                    transform={(body) => ({ ...body, file_size_bytes: Number(body.file_size_bytes) })}
                    submitLabel="Record document version"
                    successTitle="Document metadata recorded"
                    successMessage="PMS stored the version metadata and URL; no binary upload was performed."
                    compact
                  />
                </>
              )}
              {can("pms.coinventor.manage") && detail.data.coinventors.length > 0 && (
                <Stack gap="sm">
                  <Text fw={600} size="sm">Inventor agreements and withdrawal consent</Text>
                  {detail.data.coinventors.map((inventor) => (
                    <Card key={inventor.id} withBorder padding="sm">
                      <Text size="sm" fw={500}>{inventor.name} · {inventor.ownership_percentage}%</Text>
                      <PmsActionForm
                        title="Record agreement consent"
                        path={() => `/coinventors/${inventor.id}/consent/`}
                        fields={[
                          { name: "consent_given", label: "Consent given", type: "checkbox", initialValue: inventor.consent_given },
                          { name: "agreement_signed", label: "Agreement signed", type: "checkbox", initialValue: inventor.agreement_signed },
                          { name: "electronic_signature", label: "Electronic signature (when legally permitted/configured)" },
                        ]}
                        submitLabel="Save consent"
                        compact
                      />
                      <PmsActionForm
                        title="Record withdrawal consent"
                        path={() => `/coinventors/${inventor.id}/withdrawal-consent/`}
                        fields={[{ name: "withdrawal_consent_given", label: "Withdrawal consent given", type: "checkbox", initialValue: inventor.withdrawal_consent_given }]}
                        submitLabel="Save withdrawal consent"
                        compact
                      />
                    </Card>
                  ))}
                </Stack>
              )}
              <Group justify="flex-end">
                <Button variant="subtle" rightSection={<FaArrowRight size={11} />}
                  onClick={() => setSelectedId(undefined)}>
                  Close details
                </Button>
              </Group>

              {can("pms.application.revise") && ["needs_revision", "rejected", "remanded_for_amendment"].includes(detail.data.status) && (
                <PmsActionForm
                  title="Revise and resubmit"
                  path={() => `/applications/${detail.data!.id}/revise/`}
                  submitLabel="Resubmit application"
                  successTitle="Revision submitted"
                  successMessage="The updated application was recorded by PMS."
                  fields={[
                    { name: "feedback_response", label: "Response to Director feedback", type: "textarea", required: true },
                    { name: "title", label: "Updated title" },
                    { name: "abstract", label: "Updated abstract", type: "textarea" },
                    { name: "detailed_description", label: "Updated description", type: "textarea" },
                    { name: "claims", label: "Updated claims", type: "textarea" },
                  ]}
                />
              )}
              {can("pms.application.withdraw") && [
                "submitted", "under_review", "needs_revision", "resubmitted", "rejected", "approved",
              ].includes(detail.data.status) && (
                <PmsActionForm
                  title="Withdraw application"
                  path={() => `/applications/${detail.data!.id}/withdraw/`}
                  submitLabel="Withdraw"
                  successTitle="Withdrawal recorded"
                  fields={[{ name: "reason", label: "Reason", type: "textarea", required: true }]}
                  transform={(body) => ({ reason: body.reason })}
                  compact
                />
              )}
              {can("pms.application.appeal") && detail.data.status === "rejected" && (
                <PmsActionForm
                  title="File an appeal"
                  path={() => `/applications/${detail.data!.id}/appeal/`}
                  submitLabel="Submit appeal"
                  fields={[
                    { name: "grounds", label: "Grounds", type: "textarea", required: true },
                    { name: "justification", label: "Justification", type: "textarea", required: true },
                  ]}
                />
              )}
            </Stack>
          )}
        </Card>
      )}
    </Container>
  );
}
