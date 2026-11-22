import { Card, Container, Select, SimpleGrid, Text } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDepartmentReport } from "../api/hooks";

function MetricCard({ label, value }: { label: string; value: string | number | undefined }) {
  return (
    <Card padding="md" withBorder>
      <Text size="xs" c="dimmed" tt="uppercase">
        {label}
      </Text>
      <Text fw={700} size="xl" mt={2}>
        {value ?? "—"}
      </Text>
    </Card>
  );
}

export default function ReportsPage() {
  const [department, setDepartment] = useState<string>("CSE");
  const { data, isPending, error } = useDepartmentReport(department);

  return (
    <Container size="xl">
      <PageHeader
        title="BADMS Reports"
        subtitle="Departmental backup coverage, storage quotas, and security metrics"
        action={
          <Select
            data={["CSE", "ECE", "ME", "Design", "NS", "Liberal Arts"]}
            value={department}
            onChange={(val) => val && setDepartment(val)}
            allowDeselect={false}
            size="xs"
            w={160}
          />
        }
      />

      {error ? (
        <ErrorState error={error} />
      ) : isPending ? (
        <Text c="dimmed">Loading department report…</Text>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="md">
          <MetricCard label="Archival Requests" value={data?.total_archival_requests} />
          <MetricCard label="Storage Extensions" value={data?.total_storage_extensions} />
          <MetricCard
            label="Archival Approved"
            value={data?.archival_by_status?.approved ?? 0}
          />
          <MetricCard
            label="Storage Approved"
            value={data?.storage_by_status?.approved ?? 0}
          />
        </SimpleGrid>
      )}
    </Container>
  );
}
