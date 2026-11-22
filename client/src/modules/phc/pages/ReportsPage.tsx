import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Select, SimpleGrid, Stack, Table,
  Text,
} from "@mantine/core";
import { FaChartBar, FaInfoCircle, FaSync } from "react-icons/fa";
import type { IconType } from "react-icons";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAdminReport } from "../api/hooks";
import type { AdminReport, ReportCategory } from "../api/types";

const CATEGORIES = [
  { value: "demographics", label: "Patient demographics" },
  { value: "utilization", label: "Service utilization" },
  { value: "inventory", label: "Inventory" },
];

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card padding="md" withBorder>
      <Text size="xs" c="dimmed" tt="uppercase">{label}</Text>
      <Text fw={700} size="xl" mt={2}>{value}</Text>
    </Card>
  );
}

function ReportEmpty({ icon: Icon, title, description }: {
  icon: IconType;
  title: string;
  description: string;
}) {
  return (
    <Stack align="center" gap={6} py="xl">
      <Icon size={24} color="var(--mantine-color-gray-5)" />
      <Text fw={600}>{title}</Text>
      <Text size="sm" c="dimmed">{description}</Text>
    </Stack>
  );
}

function ReportBody({ report }: { report: AdminReport | undefined }) {
  if (!report) return <Text c="dimmed">Loading…</Text>;
  if (report.error) {
    return (
      <Alert variant="light" color="orange" icon={<FaInfoCircle />}>
        <Text size="sm">{report.error}</Text>
      </Alert>
    );
  }

  if (report.category === "demographics") {
    const kinds = Object.entries(report.patient_count_by_kind ?? {});
    if (kinds.length === 0) {
      return (
        <ReportEmpty
          icon={FaChartBar} title="No patients on record"
          description="Counts appear once patient profiles have been created."
        />
      );
    }
    return (
      <Stack gap="sm">
        {kinds.map(([kind, count]) => (
          <Group key={kind} justify="space-between">
            <Text size="sm">{kind}</Text>
            <Badge variant="light">{count}</Badge>
          </Group>
        ))}
      </Stack>
    );
  }

  if (report.category === "utilization") {
    const counts = [
      ["Visits", report.visits ?? 0],
      ["Prescriptions", report.prescriptions ?? 0],
      ["Ambulance logs", report.ambulance_logs ?? 0],
      ["Claims", report.claims ?? 0],
      ["Requisitions", report.requisitions ?? 0],
    ] as const;
    if (counts.every(([, n]) => n === 0)) {
      return (
        <ReportEmpty
          icon={FaChartBar} title="No activity recorded"
          description="Aggregate service counts will appear here."
        />
      );
    }
    return (
      <SimpleGrid cols={{ base: 2, sm: 3 }}>
        {counts.map(([label, value]) => (
          <Metric key={label} label={label} value={value} />
        ))}
      </SimpleGrid>
    );
  }

  const low = report.low_stock_items ?? [];
  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 2, sm: 3 }}>
        <Metric label="Items" value={report.items ?? 0} />
        <Metric label="Stock adjustments" value={report.stock_adjustments ?? 0} />
        <Metric label="Low stock" value={low.length} />
      </SimpleGrid>
      {low.length === 0 ? (
        <ReportEmpty
          icon={FaChartBar} title="Nothing below threshold"
          description="No stocked item is currently below its reorder level."
        />
      ) : (
        <Table>
          <Table.Thead>
            <Table.Tr><Table.Th>Low stock item</Table.Th></Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {low.map((name) => (
              <Table.Tr key={name}><Table.Td>{name}</Table.Td></Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}

export default function ReportsPage() {
  const { can } = useAuth();
  const canGenerate = can("phc.reports.generate");
  const [category, setCategory] = useState<ReportCategory>("demographics");
  const { data, isPending, error, refetch } = useAdminReport(category);

  if (!canGenerate) {
    return (
      <Container size="lg">
        <Alert variant="light" color="red">
          You do not have permission to generate administrative reports.
        </Alert>
      </Container>
    );
  }
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  return (
    <Container size="lg">
      <PageHeader
        title="Administrative Reports"
        subtitle="Anonymised figures — counts only, never patient-identifiable data"
        action={
          <Button
            variant="default" size="xs" leftSection={<FaSync size={11} />}
            loading={isPending} onClick={() => refetch()}
          >
            Refresh
          </Button>
        }
      />

      <Card padding="lg" mb="md">
        <Select
          label="Report" data={CATEGORIES} value={category}
          onChange={(v) => v && setCategory(v as ReportCategory)}
          allowDeselect={false} w={260}
        />
      </Card>

      <Card padding="lg">
        <ReportBody report={data} />
      </Card>

      <Text size="xs" c="dimmed" mt="sm">
        {data?.note ?? "Reports contain aggregate counts only."}
      </Text>
    </Container>
  );
}
