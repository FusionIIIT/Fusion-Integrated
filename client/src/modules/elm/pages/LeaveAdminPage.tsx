import { useEffect, useState } from "react";
import { Button, Card, Container, Group, Select, Stack, Text, Textarea, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCalendars, useCreateCalendar, useCreateOfflineRecord, useOfflineRecords, useMaintainOfflineRecord, usePolicy, usePublishCalendar, useSavePolicy, useSaveSlaConfig, useSlaConfig } from "../api";
export default function LeaveAdminPage() {
  const query = usePolicy(); const save = useSavePolicy();
  const calendars = useCalendars(); const createCalendar = useCreateCalendar(); const publishCalendar = usePublishCalendar();
  const createOffline = useCreateOfflineRecord(); const offlineRecords = useOfflineRecords(); const maintainOffline = useMaintainOfflineRecord();
  const slaQuery = useSlaConfig(); const saveSla = useSaveSlaConfig();
  const [reminderHours, setReminderHours] = useState(""); const [escalationHours, setEscalationHours] = useState(""); const [escalationRole, setEscalationRole] = useState("");
  const [params, setParams] = useState("{}"); const [hierarchy, setHierarchy] = useState("{}");
  const [calendarName, setCalendarName] = useState(""); const [calendarDate, setCalendarDate] = useState(""); const [entries, setEntries] = useState("[]");
  const [offlineUser, setOfflineUser] = useState(""); const [offlineCategory, setOfflineCategory] = useState<string | null>("CL");
  const [offlineStart, setOfflineStart] = useState(""); const [offlineEnd, setOfflineEnd] = useState(""); const [offlineReference, setOfflineReference] = useState("");
  const [maintenanceId, setMaintenanceId] = useState(""); const [maintenanceReference, setMaintenanceReference] = useState(""); const [maintenanceNote, setMaintenanceNote] = useState(""); const [maintenanceEvidence, setMaintenanceEvidence] = useState("[]");
  useEffect(() => { if (query.data) { setParams(JSON.stringify(query.data.params, null, 2)); setHierarchy(JSON.stringify(query.data.hierarchy, null, 2)); } }, [query.data]);
  useEffect(() => { if (slaQuery.data) { setReminderHours(slaQuery.data.reminder_hours == null ? "" : String(slaQuery.data.reminder_hours)); setEscalationHours(slaQuery.data.escalation_hours == null ? "" : String(slaQuery.data.escalation_hours)); setEscalationRole(slaQuery.data.escalation_role ?? ""); } }, [slaQuery.data]);
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  function submit() {
    try {
      const data = { params: JSON.parse(params) as Record<string, unknown>, hierarchy: JSON.parse(hierarchy) as Record<string, unknown> };
      save.mutate(data, { onSuccess: () => notifications.show({ color: "green", title: "Configuration saved", message: "Current leave policy and hierarchy were updated." }), onError: (e) => notifications.show({ color: "red", title: "Save failed", message: errorMessage(e) }) });
    } catch { notifications.show({ color: "red", title: "Invalid JSON", message: "Policy and hierarchy must both be valid JSON objects." }); }
  }
  return <Container size="lg"><PageHeader title="Leave Administration" subtitle="Maintain current policy parameters and approval hierarchy. This baseline does not version/publish leave-policy parameters." />
    {query.isPending ? <Text c="dimmed">Loading current configuration…</Text> : <Stack>
      <Card withBorder><Stack><Title order={3}>Policy parameters (JSON)</Title><Textarea minRows={14} autosize value={params} onChange={(e) => setParams(e.currentTarget.value)} /><Text size="sm" c="dimmed">Defaults: CL 8, RH 2, SCL 15, EL 30 for staff, COL 20, VL 60 for faculty. Keep entitlement values and optional evidence/SLA parameters explicit.</Text></Stack></Card>
      <Card withBorder><Stack><Title order={3}>Approval hierarchy (JSON)</Title><Textarea minRows={12} autosize value={hierarchy} onChange={(e) => setHierarchy(e.currentTarget.value)} /><Text size="sm" c="dimmed">Configure unit_heads by employee department and sanctioning roles by leave category. Missing mappings are refused at submission.</Text></Stack></Card>
      <Button loading={save.isPending} onClick={submit}>Save current configuration</Button>
      <Card withBorder><Stack><Title order={3}>Workflow SLA thresholds</Title>
        <Group grow><TextInput label="Reminder after (hours)" type="number" min={0} value={reminderHours} onChange={(e) => setReminderHours(e.currentTarget.value)} placeholder="Disabled when blank" /><TextInput label="Escalation after (hours)" type="number" min={0} value={escalationHours} onChange={(e) => setEscalationHours(e.currentTarget.value)} placeholder="Disabled when blank" /></Group>
        <TextInput label="Escalation target designation" value={escalationRole} onChange={(e) => setEscalationRole(e.currentTarget.value)} />
        <Button loading={saveSla.isPending} onClick={() => saveSla.mutate({ reminder_hours: reminderHours === "" ? null : Number(reminderHours), escalation_hours: escalationHours === "" ? null : Number(escalationHours), escalation_role: escalationRole }, { onSuccess: () => notifications.show({ color: "green", title: "SLA configuration saved", message: "Reminder and escalation thresholds are active for subsequent workflow stages." }), onError: (e) => notifications.show({ color: "red", title: "SLA save failed", message: errorMessage(e) }) })}>Save SLA thresholds</Button>
      </Stack></Card>
      <Card withBorder><Stack><Title order={3}>Holiday / RH / vacation calendar</Title>
        <TextInput label="Calendar name" value={calendarName} onChange={(e) => setCalendarName(e.currentTarget.value)} required />
        <TextInput label="Effective from" type="date" value={calendarDate} onChange={(e) => setCalendarDate(e.currentTarget.value)} required />
        <Textarea label="Calendar entries (JSON array)" minRows={7} autosize value={entries} onChange={(e) => setEntries(e.currentTarget.value)} />
        <Text size="sm" c="dimmed">Each entry: {`{"kind":"restricted_holiday","start_date":"2026-11-01","end_date":"2026-11-01","label":"Example"}`}. Kinds: closed_holiday, restricted_holiday, vacation.</Text>
        <Button loading={createCalendar.isPending} onClick={() => { try { createCalendar.mutate({ name: calendarName, effective_from: calendarDate, entries: JSON.parse(entries) as { kind: string; start_date: string; end_date: string; label?: string }[] }, { onSuccess: () => notifications.show({ color: "green", title: "Calendar saved", message: "Draft calendar created." }), onError: (e) => notifications.show({ color: "red", title: "Calendar failed", message: errorMessage(e) }) }); } catch { notifications.show({ color: "red", title: "Invalid JSON", message: "Calendar entries must be a JSON array." }); } }} disabled={!calendarName || !calendarDate}>Create draft calendar</Button>
        {calendars.data?.map((calendar) => <Card key={calendar.id} withBorder padding="sm"><Group justify="space-between"><Stack gap={2}><Text fw={600}>{calendar.name}</Text><Text size="sm" c="dimmed">Effective {calendar.effective_from} · {calendar.status} · {calendar.entries.length} entries</Text></Stack>{calendar.status === "draft" && <Button size="xs" onClick={() => publishCalendar.mutate(calendar.id, { onSuccess: () => notifications.show({ color: "green", title: "Calendar published", message: "This calendar is now eligible for date validation." }), onError: (e) => notifications.show({ color: "red", title: "Publish failed", message: errorMessage(e) }) })}>Publish</Button>}</Group></Card>)}
      </Stack></Card>
      <Card withBorder><Stack><Title order={3}>Record already-sanctioned offline leave</Title>
        <TextInput label="Employee ID" value={offlineUser} onChange={(e) => setOfflineUser(e.currentTarget.value)} inputMode="numeric" required />
        <Select label="Category" data={["CL", "RH", "SCL", "EL", "COL", "VL"].map((value) => ({ value, label: value }))} value={offlineCategory} onChange={setOfflineCategory} />
        <Group grow><TextInput label="Start date" type="date" value={offlineStart} onChange={(e) => setOfflineStart(e.currentTarget.value)} /><TextInput label="End date" type="date" value={offlineEnd} onChange={(e) => setOfflineEnd(e.currentTarget.value)} /></Group>
        <TextInput label="Sanction reference" value={offlineReference} onChange={(e) => setOfflineReference(e.currentTarget.value)} />
        <Button loading={createOffline.isPending} disabled={!offlineUser || !offlineCategory || !offlineStart || !offlineEnd || !offlineReference} onClick={() => createOffline.mutate({ user_id: Number(offlineUser), category: offlineCategory, start_date: offlineStart, end_date: offlineEnd, sanction_reference: offlineReference }, { onSuccess: () => notifications.show({ color: "green", title: "Offline leave recorded", message: "The existing sanction has been synchronized into ELM." }), onError: (e) => notifications.show({ color: "red", title: "Record failed", message: errorMessage(e) }) })}>Record offline sanction</Button>
        <Title order={4}>Existing offline records</Title>
        {offlineRecords.data?.map((record) => <Card key={record.id} withBorder padding="sm"><Text fw={600}>#{record.id} · Employee {record.user_id} · {record.category}</Text><Text size="sm" c="dimmed">{record.start_date} – {record.end_date} · {record.days} day(s) · {record.sanction_reference}</Text></Card>)}
        <Title order={4}>Maintain an existing record</Title>
        <TextInput label="Offline record ID" value={maintenanceId} onChange={(e) => setMaintenanceId(e.currentTarget.value)} inputMode="numeric" />
        <TextInput label="Corrected sanction reference (optional)" value={maintenanceReference} onChange={(e) => setMaintenanceReference(e.currentTarget.value)} />
        <Textarea label="Maintenance note" value={maintenanceNote} onChange={(e) => setMaintenanceNote(e.currentTarget.value)} />
        <Textarea label="Replacement evidence JSON array (optional)" value={maintenanceEvidence} onChange={(e) => setMaintenanceEvidence(e.currentTarget.value)} />
        <Button loading={maintainOffline.isPending} disabled={!maintenanceId || (!maintenanceReference && !maintenanceNote && maintenanceEvidence === "[]")} onClick={() => { try { maintainOffline.mutate({ id: Number(maintenanceId), ...(maintenanceReference ? { sanction_reference: maintenanceReference } : {}), ...(maintenanceNote ? { note: maintenanceNote } : {}), ...(maintenanceEvidence !== "[]" ? { evidence: JSON.parse(maintenanceEvidence) as unknown[] } : {}) }, { onSuccess: () => notifications.show({ color: "green", title: "Record maintained", message: "The permitted correction was saved and audited." }), onError: (e) => notifications.show({ color: "red", title: "Maintenance failed", message: errorMessage(e) }) }); } catch { notifications.show({ color: "red", title: "Invalid evidence JSON", message: "Evidence must be a JSON array." }); } }}>Save permitted correction</Button>
        <Text size="sm" c="dimmed">Record maintenance cannot change the employee, leave dates, category, or sanction status.</Text>
      </Stack></Card>
    </Stack>}
  </Container>;
}
