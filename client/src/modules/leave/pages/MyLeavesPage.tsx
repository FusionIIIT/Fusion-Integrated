import { useEffect, useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { errorMessage } from "../../../lib/http";
import { saveBlob } from "../../../lib/download";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";
import type { LeaveApplication } from "../api/types";

const color = (status: string) => {
  if (["approved", "resumption_reviewed"].includes(status)) return "green";
  if (["rejected", "cancelled"].includes(status)) return "red";
  if (status === "withdrawn") return "gray";
  return "blue";
};

export default function MyLeavesPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try { setLoading(true); setRows(await leaveApi.getMyApplications()); }
    catch (error) { notifications.show({ title: "Could not load leave requests", message: errorMessage(error), color: "red" }); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);

  async function action(title: string, run: () => Promise<unknown>) {
    try { await run(); notifications.show({ title, message: "Request updated successfully.", color: "teal" }); await refresh(); }
    catch (error) { notifications.show({ title: "Action failed", message: errorMessage(error), color: "red" }); }
  }

  return <Container size="xl">
    <PageHeader title="My Leaves" subtitle="Track applications, decisions, cancellation, extensions, and resumption." action={<Button onClick={() => navigate("/leave/apply")}>Apply for Leave</Button>} />
    {loading ? <Text>Loading leave applications…</Text> : rows.length === 0 ? <Card withBorder><Text>No leave applications found.</Text></Card> :
      <Stack>
        {rows.map((row) => <Card key={row.id} withBorder padding="md">
          <Group justify="space-between" align="flex-start">
            <Stack gap={4}>
              <Title order={5}>#{row.id} · {row.category}{row.half_day_type !== "full" ? ` · ${row.half_day_type}` : ""}</Title>
              <Text size="sm">{row.start_date} → {row.end_date} · {row.days_count} day(s)</Text>
              <Text size="sm">{row.purpose}</Text>
              <Badge color={color(row.status)}>{row.status.replace(/_/g, " ").toUpperCase()}</Badge>
              {row.resumption_outcome && <Text size="xs" c="dimmed">Resumption outcome: {row.resumption_outcome.replace(/_/g, " ")}</Text>}
            </Stack>
            <Group gap="xs">
              <Button size="xs" variant="light" onClick={() => void action("Export prepared", async () => saveBlob(await leaveApi.exportApplication(row.id), `leave-application-${row.id}.csv`))}>Export</Button>
              <Button size="xs" variant="subtle" onClick={() => void action("Print view prepared", async () => saveBlob(await leaveApi.printApplication(row.id), `leave-application-${row.id}.html`))}>Print</Button>
              {["substitute_pending", "under_review", "extension_requested"].includes(row.status) &&
                <Button size="xs" color="red" variant="subtle" onClick={() => { const reason = window.prompt("Reason for withdrawal", "Withdrawn by employee"); if (reason !== null) void action("Application withdrawn", () => leaveApi.withdrawApplication(row.id, reason)); }}>Withdraw</Button>}
              {row.status === "approved" && <>
                <Button size="xs" color="orange" variant="outline" onClick={() => { const reason = window.prompt("Reason for cancellation"); if (reason?.trim()) void action("Cancellation requested", () => leaveApi.requestCancellation(row.id, reason.trim())); }}>Cancel</Button>
                {["EL", "COL", "VL"].includes(row.category) && !row.resumption_reviewed_at &&
                  <Button size="xs" color="teal" variant="outline" onClick={() => { const date = window.prompt("Actual resumption date (YYYY-MM-DD)"); if (date) void action("Resumption submitted", () => leaveApi.submitResumption(row.id, date)); }}>Resume</Button>}
                {["EL", "COL", "VL"].includes(row.category) &&
                  <Button size="xs" variant="outline" onClick={() => {
                    const start = new Date(`${row.end_date}T00:00:00`); start.setDate(start.getDate() + 1);
                    const startDate = `${start.getFullYear()}-${String(start.getMonth()+1).padStart(2,"0")}-${String(start.getDate()).padStart(2,"0")}`;
                    const end = window.prompt("Extension end date (YYYY-MM-DD)", startDate);
                    const purpose = end && window.prompt("Reason for extension");
                    if (end && purpose?.trim()) void action("Extension requested", () => leaveApi.requestExtension(row.id, { start_date: startDate, end_date: end, purpose: purpose.trim() }));
                  }}>Extend</Button>}
              </>}
            </Group>
          </Group>
        </Card>)}
      </Stack>}
  </Container>;
}
