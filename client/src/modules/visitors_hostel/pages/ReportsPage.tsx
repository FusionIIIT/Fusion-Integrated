import { useState } from "react";
import { Alert, Button, Card, Container, Group, Select, Stack, Text } from "@mantine/core";
import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { getReport } from "../api";

const reportTypes = [
  { value: "booking_summary", permission: "visitor_hostel.report.view_in_charge" },
  { value: "category_occupancy", permission: "visitor_hostel.report.view_in_charge" },
  { value: "billing_summary", permission: "visitor_hostel.report.view_in_charge" },
  { value: "inventory_usage", permission: "visitor_hostel.report.view_in_charge" },
  { value: "daily_occupancy", permission: "visitor_hostel.report.view_caretaker" },
  { value: "arrivals_departures", permission: "visitor_hostel.report.view_caretaker" },
  { value: "pending_approvals", permission: "visitor_hostel.report.view_caretaker" },
  { value: "stay_exceptions", permission: "visitor_hostel.report.view_caretaker" },
];

export default function ReportsPage() {
  const { can } = useAuth();
  const availableReports = reportTypes.filter((r) => can(r.permission));
  const [type, setType] = useState<string | null>(availableReports[0]?.value ?? null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function generate() {
    if (!type) return;
    setLoading(true); setError("");
    try { setResult(await getReport(type)); }
    catch (e) { setError(errorMessage(e)); }
    finally { setLoading(false); }
  }
  return <Container size="xl"><PageHeader title="VHMS reports"
    subtitle="Reports are filtered by your server-side role permissions." />
    {error && <Alert color="red" mb="md">{error}</Alert>}
    <Card withBorder p="lg"><Stack>
      {!availableReports.length && <Text c="dimmed">No reports are available for your role.</Text>}
      {!!availableReports.length && <Group align="end"><Select label="Report" data={availableReports.map((r) => ({ value: r.value, label: r.value.replaceAll("_", " ") }))}
        value={type} onChange={setType} /><Button loading={loading} onClick={() => void generate()}>Generate</Button></Group>
      }
      {result && <Text component="pre" style={{ whiteSpace: "pre-wrap" }}>
        {JSON.stringify(result, null, 2)}</Text>}
    </Stack></Card>
  </Container>;
}
