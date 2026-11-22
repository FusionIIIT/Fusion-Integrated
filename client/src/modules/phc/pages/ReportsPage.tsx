import { useState } from "react";
import { Button, Card, Code, Container, Group, Select, Text, TextInput } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useReport } from "../api/hooks";
import type { ReportCategory } from "../api/types";
import { ListStates } from "../components/ListStates";

const CATEGORIES = [
  { value: "demographics", label: "Patient demographics" },
  { value: "utilization", label: "Service utilization" },
  { value: "inventory", label: "Inventory consumption" },
];

export default function ReportsPage() {
  const [category, setCategory] = useState<ReportCategory>("utilization");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [params, setParams] = useState<{
    category: ReportCategory; start: string; end: string } | null>(null);
  const report = useReport(params);

  return (
    <Container size="lg">
      <PageHeader title="Reports" subtitle="Anonymised: no report names a patient" />
      <Group align="flex-end" mb="md">
        <Select label="Report" data={CATEGORIES} value={category}
          onChange={(v) => setCategory((v ?? "utilization") as ReportCategory)} />
        <TextInput label="From" type="date" value={start}
          onChange={(e) => setStart(e.currentTarget.value)} />
        <TextInput label="To" type="date" value={end}
          onChange={(e) => setEnd(e.currentTarget.value)} />
        <Button disabled={!start || !end}
          onClick={() => setParams({ category, start, end })}>Generate</Button>
      </Group>
      {params === null && <Text c="dimmed">Choose a report and a date range.</Text>}
      {params !== null && (
        <ListStates isPending={report.isPending} error={report.error}
          empty={false} emptyText="" />
      )}
      {report.data && (
        <Card withBorder padding="lg">
          <Text fw={700} mb="xs">
            {CATEGORIES.find((c) => c.value === report.data.category)?.label}:{" "}
            {report.data.start} to {report.data.end}
          </Text>
          <Code block>{JSON.stringify(report.data.data, null, 2)}</Code>
        </Card>
      )}
    </Container>
  );
}
