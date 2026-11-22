import { useState } from "react";
import {
  Alert, Button, Container, Group, Select, Stack, Switch, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaDownload } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReportCatalogue, useReportExport, useRunReport } from "../api/hooks";
import type { ExportFormat } from "../api/types";
import { humanise } from "../format";

export default function ReportsPage() {
  const { can } = useAuth();
  const catalogue = useReportCatalogue();
  const exporter = useReportExport();
  const [key, setKey] = useState<string | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [showNames, setShowNames] = useState(false);

  const params: Record<string, string> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  if (showNames) params.anonymize = "false";

  const report = useRunReport(key, params);
  const def = catalogue.data?.find((d) => d.key === key);
  const canExport = can("vms.report.export");
  const canSeeNames = can("vms.report.view_pii");

  if (catalogue.error) return <Container size="lg"><ErrorState error={catalogue.error} /></Container>;

  function download(fmt: ExportFormat) {
    if (!key) return;
    exporter.mutate({ key, params, fmt }, {
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  const columns = report.data?.columns ?? [];

  return (
    <Container size="lg">
      <PageHeader title="Reports" subtitle="Visitor statistics, compliance and audit reports" />

      <Stack gap="md" mb="lg">
        <Group align="flex-end" wrap="wrap">
          <Select
            label="Report" placeholder="Choose a report" w={280} searchable
            data={(catalogue.data ?? []).map((d) => ({ value: d.key, label: d.title }))}
            value={key} onChange={setKey}
          />
          <TextInput label="From" type="date" value={start}
            onChange={(e) => setStart(e.currentTarget.value)} />
          <TextInput label="To" type="date" value={end}
            onChange={(e) => setEnd(e.currentTarget.value)} />
          {canSeeNames && def?.identity && (
            <Switch label="Show names and contact details" checked={showNames}
              onChange={(e) => setShowNames(e.currentTarget.checked)} />
          )}
        </Group>
        {key && canExport && (
          <Group gap="xs">
            <Button variant="default" size="compact-sm" leftSection={<FaDownload size={11} />}
              loading={exporter.isPending && exporter.variables?.fmt === "csv"}
              onClick={() => download("csv")}>
              Download CSV
            </Button>
            <Button variant="default" size="compact-sm" leftSection={<FaDownload size={11} />}
              loading={exporter.isPending && exporter.variables?.fmt === "pdf"}
              onClick={() => download("pdf")}>
              Download PDF
            </Button>
          </Group>
        )}
        {showNames && (
          <Alert color="orange" variant="light">
            Names and contact details are personal data. Viewing and exporting them is recorded
            in the audit trail.
          </Alert>
        )}
      </Stack>

      {key === null && <Text c="dimmed">Choose a report to see it here.</Text>}
      {key !== null && report.error && <ErrorState error={report.error} />}
      {key !== null && !report.error && (
        <>
          <DataTable<Record<string, unknown>>
            rows={report.data?.rows ?? []}
            loading={report.isPending}
            rowKey={(r) => JSON.stringify(r)}
            empty={{ title: "No data for this period" }}
            columns={columns.map((c) => ({
              key: c, header: humanise(c), render: (r) => String(r[c] ?? "—"),
            }))}
          />
          {report.data?.truncated && (
            <Text size="xs" c="dimmed" mt="sm">
              Showing the first rows only. Narrow the dates, or download the full report.
            </Text>
          )}
        </>
      )}
    </Container>
  );
}
