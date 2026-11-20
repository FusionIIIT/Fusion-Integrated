import { Card, Container, SimpleGrid, Stack, Text } from "@mantine/core";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useWorkflowOversight } from "../api/hooks";
import type { WorkflowOversight } from "../api/types";

export default function WorkflowPage() {
  const query = useWorkflowOversight();
  const columns: Column<WorkflowOversight>[] = [
    { key: "application_no", header: "Application" },
    { key: "domain", header: "Domain" },
    { key: "status", header: "Application state", render: (row) => <StatusBadge status={row.status} /> },
    { key: "director", header: "Director", render: (row) => row.assigned_director_user_id ?? "—" },
    { key: "attorney", header: "Attorney", render: (row) => row.assigned_attorney_user_id ?? "—" },
    { key: "review_deadline", header: "Review deadline", render: (row) => row.review_deadline ?? "—" },
    { key: "revision_deadline", header: "Revision deadline", render: (row) => row.revision_deadline ?? "—" },
    { key: "budget_status", header: "Budget", render: (row) => row.budget_status ? <StatusBadge status={row.budget_status} /> : "—" },
    { key: "pending", header: "Pending actions", render: (row) => row.office_actions.filter((item) => item.status !== "response_submitted").length + row.maintenance.filter((item) => item.maintenance_status === "decision_requested").length },
  ];

  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="Workflow oversight" subtitle="View lifecycle and related workflow states within the scope authorized by PMS." />
      {query.data?.length ? (
        <Stack gap="md">
          <Card padding="lg">
            <DataTable rows={query.data} columns={columns} rowKey={(row) => row.application_id}
              loading={query.isPending} minWidth={1100}
              empty={{ title: "No visible workflows", description: "No workflows are available in your authorized scope." }} />
          </Card>
          {query.data.map((row) => (
            <Card key={row.application_id} padding="md">
              <PageHeader title={`${row.application_no} · workflow details`} subtitle={`Attorney assignments: ${row.attorney_assignment_statuses.join(", ") || "none"}`} />
              <SimpleGrid cols={{ base: 1, md: 2 }}>
                <div>
                  <Text fw={600} size="sm">Office actions</Text>
                  {row.office_actions.length ? row.office_actions.map((item) => (
                    <Text key={item.id} size="sm" c="dimmed">Due {item.due_date} · {item.status} · applicant approval {item.applicant_approved ? "recorded" : "pending/not required"}</Text>
                  )) : <Text size="sm" c="dimmed">None recorded.</Text>}
                </div>
                <div>
                  <Text fw={600} size="sm">Maintenance</Text>
                  {row.maintenance.length ? row.maintenance.map((item) => (
                    <Text key={item.id} size="sm" c="dimmed">Cycle {item.cycle_number} · due {item.fee_due_date} · {item.maintenance_status}</Text>
                  )) : <Text size="sm" c="dimmed">No configured cycles recorded.</Text>}
                </div>
              </SimpleGrid>
            </Card>
          ))}
        </Stack>
      ) : query.isPending ? <Text c="dimmed">Loading workflow oversight…</Text> : (
        <Card padding="lg"><Text c="dimmed">No workflow records are available in your authorized scope.</Text></Card>
      )}
    </Container>
  );
}
