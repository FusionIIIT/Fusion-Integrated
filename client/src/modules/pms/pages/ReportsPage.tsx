import { Button, Container, Group, Select, Stack, Title } from "@mantine/core";
import { useState } from "react";
import { FaChartBar } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDeactivateReport, useExport, useReport, useReportDefinitions, useSaveReportDefinition,
} from "../api/hooks";
import type { ReportDefinition } from "../api/types";
import { ActionBar, action, str } from "../components/ActionBar";
import { day, words } from "../components/format";
import { usePmsCan } from "../components/access";

const OFFICE = ["status", "financial", "deadlines", "inventors", "portfolio", "workload",
  "dashboard", "history", "trend"];
const OWN = ["status", "deadlines", "inventors", "portfolio", "dashboard"];

// UC-PMS-024, 030, 031: reports within the caller's scope; viewing is logged.
export default function ReportsPage() {
  const can = usePmsCan();
  const office = can("pms.report.export");
  const types = office ? OFFICE : OWN;
  const [type, setType] = useState("status");
  const report = useReport(type);
  const download = useExport();
  const saved = useReportDefinitions(can("pms.report_definition.create"));
  const save = useSaveReportDefinition();
  const off = useDeactivateReport();
  const saveAction = can("pms.report_definition.create") ? [action({ key: "save",
    label: "Save and schedule", title: `Save the ${words(type)} report`, fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "schedule", label: "Schedule", type: "select", required: true, initial: "none",
        options: [{ value: "none", label: "Not scheduled" }, { value: "weekly", label: "Weekly" },
          { value: "monthly", label: "Monthly" }] },
    ], submitLabel: "Save" }, save, (v) => ({ name: str(v.name), report_type: type,
    schedule: str(v.schedule) }))] : [];
  const cols = report.data?.columns ?? [];
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Reports" subtitle="Only applications within your scope are counted" />
      <Stack gap="md">
        <Group align="flex-end">
          <Select label="Report" value={type} onChange={(v) => v && setType(v)}
            data={types.map((t) => ({ value: t, label: words(t) }))} />
          {office && (
            <Button variant="light" loading={download.isPending}
              onClick={() => download.mutate({ path: `reports/${type}/export`,
                name: `pms-${type}.csv` })}>Export CSV</Button>
          )}
          <ActionBar actions={saveAction} />
        </Group>
        {download.error != null && <ErrorState error={download.error} />}
        {report.error ? <ErrorState error={report.error} /> : (
          <DataTable<Record<string, string | number>>
            rows={report.data?.rows ?? []} loading={report.isPending}
            rowKey={(r) => cols.map((c) => String(r[c])).join("|")}
            empty={{ icon: FaChartBar, title: "Nothing to report yet" }}
            columns={cols.map((c) => ({ key: c, header: words(c) }))}
          />
        )}
        {saved.data && saved.data.length > 0 && (
          <>
            <Title order={4}>Saved reports</Title>
            <DataTable<ReportDefinition>
              rows={saved.data} rowKey={(r) => r.id} empty={{ title: "No saved reports" }}
              columns={[
                { key: "name", header: "Name" },
                { key: "report_type", header: "Report", render: (r) => words(r.report_type) },
                { key: "schedule", header: "Schedule", render: (r) => words(r.schedule) },
                { key: "runs", header: "Latest run", render: (r) => {
                  const run = r.runs[0];
                  return run ? (
                    <Button size="xs" variant="subtle" onClick={() => download.mutate({
                      path: `report-runs/${run.id}/download`, name: `${r.name}.csv` })}>
                      {run.period} ({day(run.created_at)})
                    </Button>) : "—";
                } },
                { key: "act", header: "", align: "right", render: (r) => r.active ? (
                  <Button size="xs" variant="subtle" color="red"
                    onClick={() => off.mutate(r.id)}>Switch off</Button>) : "Off" },
              ]}
            />
          </>
        )}
      </Stack>
    </Container>
  );
}
