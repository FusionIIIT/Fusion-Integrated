import { useState } from "react";
import { Button, Card, Container, Stack, Text } from "@mantine/core";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePmsApplication, usePmsApplications } from "../api/hooks";
import type { PatentApplication } from "../api/types";
import { PmsActionForm } from "../components/PmsActionForm";

export default function ApplicationQueuePage() {
  const [selectedId, setSelectedId] = useState<number>();
  const list = usePmsApplications();
  const detail = usePmsApplication(selectedId);

  if (list.error) return <Container size="xl"><ErrorState error={list.error} /></Container>;
  const columns: Column<PatentApplication>[] = [
    { key: "application_no", header: "Application" },
    { key: "title", header: "Invention" },
    { key: "domain", header: "Domain" },
    { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
    {
      key: "manage", header: "", align: "right",
      render: (row) => <Button size="xs" variant="light" onClick={() => setSelectedId(row.id)}>Manage</Button>,
    },
  ];

  return (
    <Container size="xl">
      <PageHeader title="Application queue" subtitle="Applications available within your PMS authorization scope." />
      <Card padding="lg">
        <DataTable rows={list.data ?? []} columns={columns} rowKey={(row) => row.id}
          loading={list.isPending} minWidth={800}
          empty={{ title: "Queue is empty", description: "No applications are currently visible to your role." }} />
      </Card>
      {selectedId != null && (
        <Card padding="lg" mt="md">
          {detail.error ? <ErrorState error={detail.error} /> : detail.isPending ? (
            <Text c="dimmed">Loading application…</Text>
          ) : detail.data && (
            <Stack gap="md">
              <PageHeader title={`${detail.data.application_no} · ${detail.data.title}`}
                subtitle={`Current status: ${detail.data.status.replace(/_/g, " ")}`} />
              {detail.data.status === "submitted" || detail.data.status === "resubmitted" ? (
                <PmsActionForm
                  title="Assign Director"
                  path={() => `/applications/${detail.data!.id}/assign-director/`}
                  fields={[{ name: "director_user_id", label: "Director IAM user ID", type: "number", required: true }]}
                  transform={(body) => ({ director_user_id: Number(body.director_user_id) })}
                  successTitle="Director assigned"
                  successMessage="PMS recorded the assignment and started the review workflow."
                  submitLabel="Assign Director"
                />
              ) : null}
              {detail.data.status === "approved" && (
                <PmsActionForm
                  title="Assign Attorney"
                  path={() => `/applications/${detail.data!.id}/assign-attorney/`}
                  fields={[
                    { name: "attorney_user_id", label: "Attorney IAM user ID", type: "number", required: true },
                    { name: "institutional_exception", label: "Approved institutional exception", type: "checkbox" },
                  ]}
                  transform={(body) => ({
                    attorney_user_id: Number(body.attorney_user_id),
                    institutional_exception: body.institutional_exception,
                  })}
                  successTitle="Attorney assignment offered"
                  successMessage="PMS recorded the offer. The Attorney must respond to it."
                  submitLabel="Offer assignment"
                />
              )}
              {detail.data.attorney_assignments.length > 0 && (
                <Card withBorder padding="sm">
                  <Text size="sm" fw={600}>Attorney assignment history</Text>
                  {detail.data.attorney_assignments.map((assignment) => (
                    <Text size="sm" key={assignment.id}>
                      User {assignment.attorney_user_id} · {assignment.status}
                      {assignment.is_active ? " · active" : ""}
                    </Text>
                  ))}
                </Card>
              )}
            </Stack>
          )}
        </Card>
      )}
    </Container>
  );
}
