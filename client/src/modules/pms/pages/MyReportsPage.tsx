import {
  Card,
  Container,
  Group,
  Paper,
  SimpleGrid,
  Text,
} from "@mantine/core";
import { FaAward, FaFileAlt, FaHourglassHalf } from "react-icons/fa";

import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplicationListItem } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

export default function MyReportsPage() {
  const { data, isPending, error } = useApplications();

  const total = data?.results?.length ?? 0;
  const granted = data?.results?.filter((a) => a.status === "granted").length ?? 0;
  const inProsecution =
    data?.results?.filter((a) =>
      ["under_review", "attorney_assigned", "filed", "office_action_received"].includes(
        a.status
      )
    ).length ?? 0;

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
      header: "Title",
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
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "submitted_at",
      header: "Filing / Submission Date",
      render: (row) => (
        <Text size="xs">
          {row.submitted_at ? new Date(row.submitted_at).toLocaleDateString() : "Draft"}
        </Text>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Inventor Portfolio Report"
        subtitle="Personal intellectual property portfolio, filing velocity, and granted patent assets."
      />

      <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
        <Paper p="md" withBorder>
          <Group>
            <FaFileAlt size={28} color="#228be6" />
            <div>
              <Text size="xs" c="dimmed" fw={700}>
                TOTAL DISCLOSURES
              </Text>
              <Text fw={700} size="xl">
                {total}
              </Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group>
            <FaHourglassHalf size={28} color="#fd7e14" />
            <div>
              <Text size="xs" c="dimmed" fw={700}>
                ACTIVE PROSECUTION
              </Text>
              <Text fw={700} size="xl">
                {inProsecution}
              </Text>
            </div>
          </Group>
        </Paper>

        <Paper p="md" withBorder>
          <Group>
            <FaAward size={28} color="#12b886" />
            <div>
              <Text size="xs" c="dimmed" fw={700}>
                PATENTS GRANTED
              </Text>
              <Text fw={700} size="xl">
                {granted}
              </Text>
            </div>
          </Group>
        </Paper>
      </SimpleGrid>

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No applications found",
            description: "No patent disclosures in personal portfolio.",
          }}
        />
      </Card>
    </Container>
  );
}
