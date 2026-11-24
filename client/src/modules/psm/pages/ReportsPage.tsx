// Operational, procurement, stock, and financial reports, CSV export, and schedules (PSM-UC-010, 015, 031).
import { useState } from "react";
import { Badge, Button, Card, Container, Group, Select, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateReportSchedule,
  useExportReportCsv,
  useGenerateReport,
  useReportLogs,
  useReportSchedules,
  useRunReportSchedule,
} from "../api/hooks";
import type { ReportGenerationLog, ReportResult, ReportSchedule } from "../api/types";

export default function ReportsPage() {
  const { can } = useAuth();
  const schedules = useReportSchedules();
  const logs = useReportLogs();
  const generate = useGenerateReport();
  const exportCsv = useExportReportCsv();
  const createSched = useCreateReportSchedule();
  const runSched = useRunReportSchedule();

  const [reportType, setReportType] = useState("operational");
  const [result, setResult] = useState<ReportResult | null>(null);
  const [scheduling, setScheduling] = useState(false);
  const [schedName, setSchedName] = useState("");
  const [cadence, setCadence] = useState("weekly");

  const types = can("psm.financial_report.view")
    ? ["operational", "procurement", "stock", "financial"]
    : ["operational", "procurement", "stock"];

  if (schedules.error) return <Container size="xl"><ErrorState error={schedules.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Reports & Schedules"
        subtitle="Generate, export, and schedule authorized procurement and stores reports"
        action={can("psm.report.create") ? <Button onClick={() => setScheduling(true)}>Schedule report</Button> : undefined}
      />

      <Stack gap="lg">
        <Card padding="lg" withBorder>
          <Group align="flex-end" gap="sm">
            <Select label="Report type" data={types} value={reportType} onChange={(v) => setReportType(v ?? "operational")} />
            <Button
              loading={generate.isPending}
              onClick={() =>
                generate.mutate(
                  { report_type: reportType },
                  {
                    onSuccess: (res) => setResult(res),
                    onError: (e) => notifications.show({ color: "red", title: "Report failed", message: errorMessage(e) }),
                  },
                )
              }
            >
              Generate report
            </Button>
            {can("psm.report.export") && (
              <Button
                variant="light"
                loading={exportCsv.isPending}
                onClick={() =>
                  exportCsv.mutate(
                    { report_type: reportType },
                    {
                      onError: (e) => notifications.show({ color: "red", title: "Export failed", message: errorMessage(e) }),
                    },
                  )
                }
              >
                Export CSV
              </Button>
            )}
          </Group>
          {result && (
            <Text size="sm" mt="sm">
              Generated {result.report_type} report (log #{result.log_id}): {result.row_count} row(s).
            </Text>
          )}
        </Card>

        <Card padding="lg">
          <Title order={4} mb="sm">Scheduled Reports</Title>
          <DataTable<ReportSchedule>
            rows={schedules.data?.results ?? []}
            loading={schedules.isPending}
            rowKey={(r) => r.id}
            empty={{ title: "No scheduled reports configured." }}
            columns={[
              { key: "name", header: "Schedule", render: (r) => r.name },
              { key: "type", header: "Report Type", render: (r) => r.report_type },
              { key: "cadence", header: "Cadence", render: (r) => r.cadence },
              {
                key: "last_run",
                header: "Last Run",
                render: (r) => (r.last_run_at ? new Date(r.last_run_at).toLocaleString() : "—"),
              },
              { key: "active", header: "State", render: (r) => <Badge color={r.is_active ? "green" : "gray"}>{r.is_active ? "Active" : "Paused"}</Badge> },
              {
                key: "action",
                header: "Actions",
                render: (r) =>
                  can("psm.report.create") && r.is_active ? (
                    <Button
                      size="xs"
                      variant="light"
                      loading={runSched.isPending}
                      onClick={() =>
                        runSched.mutate(r.id, {
                          onSuccess: (log) =>
                            notifications.show({
                              color: "green",
                              title: "Scheduled report ran",
                              message: `Generated ${log.report_type} log #${log.id} (${log.row_count} row(s)).`,
                            }),
                          onError: (e) =>
                            notifications.show({
                              color: "red",
                              title: "Scheduled run failed",
                              message: errorMessage(e),
                            }),
                        })
                      }
                    >
                      Run now
                    </Button>
                  ) : (
                    "—"
                  ),
              },
            ]}
          />
        </Card>

        <Card padding="lg">
          <Title order={4} mb="sm">Report Generation Logs</Title>
          <DataTable<ReportGenerationLog>
            rows={logs.data?.results ?? []}
            loading={logs.isPending}
            rowKey={(r) => r.id}
            empty={{ title: "No report runs logged yet." }}
            columns={[
              { key: "id", header: "Log ID", render: (r) => `#${r.id}` },
              { key: "type", header: "Report Type", render: (r) => r.report_type },
              { key: "trigger", header: "Trigger", render: (r) => r.trigger_type },
              { key: "schedule", header: "Schedule", render: (r) => r.schedule_name ?? "—" },
              { key: "rows", header: "Rows", render: (r) => r.row_count },
              {
                key: "status",
                header: "Status",
                render: (r) => (
                  <Badge color={r.status === "succeeded" ? "green" : r.status === "blocked" ? "yellow" : "red"}>
                    {r.status}
                  </Badge>
                ),
              },
            ]}
          />
        </Card>
      </Stack>

      <FormModal
        opened={scheduling}
        onClose={() => setScheduling(false)}
        title="Schedule Report"
        submitLabel="Save schedule"
        submitting={createSched.isPending}
        onSubmit={() =>
          createSched.mutate(
            { name: schedName, report_type: reportType, cadence },
            {
              onSuccess: () => {
                setScheduling(false);
                setSchedName("");
                notifications.show({ color: "green", title: "Scheduled", message: "Report schedule saved." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <TextInput label="Schedule name" value={schedName} onChange={(e) => setSchedName(e.currentTarget.value)} required />
          <Select label="Report type" data={types} value={reportType} onChange={(v) => setReportType(v ?? "operational")} />
          <Select label="Cadence" data={["daily", "weekly", "monthly"]} value={cadence} onChange={(v) => setCadence(v ?? "weekly")} />
        </Stack>
      </FormModal>
    </Container>
  );
}
