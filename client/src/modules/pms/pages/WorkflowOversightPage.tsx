import {
  Card,
  Container,
  Paper,
  Progress,
  SimpleGrid,
  Text,
} from "@mantine/core";

import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplicationListItem } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

export default function WorkflowOversightPage() {
  const { data, isPending, error } = useApplications();

  const applications = data?.results ?? [];
  const total = applications.length;

  const reviewCount = applications.filter((a) =>
    ["submitted", "under_review", "revisions_requested"].includes(a.status)
  ).length;

  const preFilingCount = applications.filter((a) =>
    ["approved", "assignment_offered", "attorney_assigned", "budget_approved"].includes(
      a.status
    )
  ).length;

  const prosecutionCount = applications.filter((a) =>
    ["filed", "office_action_received", "response_submitted", "hearing_scheduled"].includes(
      a.status
    )
  ).length;

  const grantedCount = applications.filter((a) =>
    ["granted", "renewal_decision_requested", "renewal_approved", "renewed"].includes(
      a.status
    )
  ).length;

  const columns: Column<PatentApplicationListItem>[] = [
    {
      key: "application_no",
      header: "Application No.",
      render: (row) => (
        <Text fw={600} size="sm">
          {row.application_no}
        </Text>
      ),
    },
    {
      key: "title",
      header: "Invention Title",
      render: (row) => (
        <Text fw={500} size="sm">
          {row.title}
        </Text>
      ),
    },
    {
      key: "domain",
      header: "Domain",
      render: (row) => <Text size="xs">{row.domain}</Text>,
    },
    {
      key: "status",
      header: "Current Stage",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "updated_at",
      header: "Last Activity",
      render: (row) => (
        <Text size="xs">{new Date(row.updated_at).toLocaleDateString()}</Text>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Institutional IP Workflow Oversight"
        subtitle="End-to-end pipeline visibility, throughput monitoring, and prosecution bottleneck tracking."
      />

      <SimpleGrid cols={{ base: 1, sm: 4 }} mb="lg">
        <Paper p="md" withBorder>
          <Text size="xs" c="dimmed" fw={700}>
            STAGE 1: INTERNAL REVIEW
          </Text>
          <Text fw={700} size="xl" c="blue">
            {reviewCount}
          </Text>
          <Progress value={total ? (reviewCount / total) * 100 : 0} color="blue" size="xs" mt="xs" />
        </Paper>

        <Paper p="md" withBorder>
          <Text size="xs" c="dimmed" fw={700}>
            STAGE 2: PRE-FILING PREP
          </Text>
          <Text fw={700} size="xl" c="cyan">
            {preFilingCount}
          </Text>
          <Progress value={total ? (preFilingCount / total) * 100 : 0} color="cyan" size="xs" mt="xs" />
        </Paper>

        <Paper p="md" withBorder>
          <Text size="xs" c="dimmed" fw={700}>
            STAGE 3: ACTIVE PROSECUTION
          </Text>
          <Text fw={700} size="xl" c="orange">
            {prosecutionCount}
          </Text>
          <Progress value={total ? (prosecutionCount / total) * 100 : 0} color="orange" size="xs" mt="xs" />
        </Paper>

        <Paper p="md" withBorder>
          <Text size="xs" c="dimmed" fw={700}>
            STAGE 4: POST-GRANT / ASSETS
          </Text>
          <Text fw={700} size="xl" c="teal">
            {grantedCount}
          </Text>
          <Progress value={total ? (grantedCount / total) * 100 : 0} color="teal" size="xs" mt="xs" />
        </Paper>
      </SimpleGrid>

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={applications}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No workflows in progress",
            description: "No patent applications currently in pipeline.",
          }}
        />
      </Card>
    </Container>
  );
}
