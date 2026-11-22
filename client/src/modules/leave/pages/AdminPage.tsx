import { useState } from "react";
import { Button, Container, NumberInput, Paper, Select, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveTypes, useCreateCalendar, useLeaveAdmin, useOfflineLeave, usePublishCalendar, useRecordCorrection, useSavePolicy, useSaveRoute, useSaveSla } from "../api/hooks";

export default function AdminPage() {
  const admin = useLeaveAdmin();
  const savePolicy = useSavePolicy();
  const saveRoute = useSaveRoute();
  const createCalendar = useCreateCalendar();
  const publish = usePublishCalendar();
  const saveSla = useSaveSla();
  const offlineLeave = useOfflineLeave();
  const correction = useRecordCorrection();
  const [leaveType, setLeaveType] = useState<string | null>("CL");
  const [entitlement, setEntitlement] = useState<number | string>(8);
  const [unitKey, setUnitKey] = useState("");
  const [unitHead, setUnitHead] = useState<number | string>("");
  const [finalAuthority, setFinalAuthority] = useState<number | string>("");
  const [calendarName, setCalendarName] = useState("");
  const [calendarStart, setCalendarStart] = useState("");
  const [calendarEnd, setCalendarEnd] = useState("");
  const [taskKind, setTaskKind] = useState("unit_head_review");
  const [reminderHours, setReminderHours] = useState<number | string>(24);
  const [employeeId, setEmployeeId] = useState<number | string>("");
  const [offlineStart, setOfflineStart] = useState("");
  const [offlineEnd, setOfflineEnd] = useState("");
  const [offlineDays, setOfflineDays] = useState<number | string>(1);
  const [sanctionReference, setSanctionReference] = useState("");
  const [adjustment, setAdjustment] = useState<number | string>(0);
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const error = admin.policies.error ?? admin.routes.error ?? admin.calendars.error ?? admin.sla.error;
  const mutate = (operation: { mutate: (value: never, options: never) => void }, value: object, label: string) =>
    operation.mutate(value as never, { onSuccess: () => notifications.show({ title: `${label} saved`, message: "The configuration was updated." }),
      onError: (reason: unknown) => notifications.show({ color: "red", title: `${label} failed`, message: errorMessage(reason) }) } as never);

  return <Container size="lg">
    <PageHeader title="Leave Administration" subtitle="Maintain current leave policy, routing, holiday calendar, and task SLA settings." />
    {error && <ErrorState error={error} />}
    <Stack>
      <Paper withBorder p="md"><Stack>
        <Text fw={600}>Current leave policy</Text>
        <Select label="Leave category" data={leaveTypes()} value={leaveType} onChange={setLeaveType} />
        <NumberInput label="Annual entitlement" value={entitlement} onChange={setEntitlement} min={0} decimalScale={2} />
        <Button onClick={() => mutate(savePolicy, { leave_type: leaveType, annual_entitlement: entitlement,
          applies_to: "all", carry_forward: ["EL", "COL"].includes(leaveType ?? ""),
          substitute_required: false, medical_evidence_required: false }, "Policy")}>Save current policy</Button>
        {(admin.policies.data ?? []).map((row) => <Text key={row.leave_type} size="sm">{row.leave_type}: {row.annual_entitlement}</Text>)}
      </Stack></Paper>
      <Paper withBorder p="md"><Stack>
        <Text fw={600}>Authority route</Text>
        <TextInput label="Organizational unit key" value={unitKey} onChange={(event) => setUnitKey(event.currentTarget.value)} />
        <Select label="Leave category" data={leaveTypes()} value={leaveType} onChange={setLeaveType} />
        <NumberInput label="Unit Head IAM user ID" value={unitHead} onChange={setUnitHead} min={1} />
        <NumberInput label="Final authority IAM user ID" value={finalAuthority} onChange={setFinalAuthority} min={1} />
        <Button disabled={!unitKey || !unitHead} onClick={() => mutate(saveRoute, { unit_key: unitKey,
          leave_type: leaveType, unit_head_user_id: unitHead, final_authority_user_id: finalAuthority || null,
          establishment_required: false, establishment_user_id: null }, "Authority route")}>Save route</Button>
        {(admin.routes.data ?? []).map((row) => <Text key={row.id} size="sm">{row.unit_key} · {row.leave_type} · Unit Head {row.unit_head_user_id}</Text>)}
      </Stack></Paper>
      <Paper withBorder p="md"><Stack>
        <Text fw={600}>Holiday / restricted holiday calendar</Text>
        <TextInput label="Calendar name" value={calendarName} onChange={(event) => setCalendarName(event.currentTarget.value)} />
        <TextInput label="Effective from" type="date" value={calendarStart} onChange={(event) => setCalendarStart(event.currentTarget.value)} />
        <TextInput label="Effective to (optional)" type="date" value={calendarEnd} onChange={(event) => setCalendarEnd(event.currentTarget.value)} />
        <Button disabled={!calendarName || !calendarStart} onClick={() => mutate(createCalendar,
          { name: calendarName, effective_from: calendarStart, effective_to: calendarEnd || null, dates: [] }, "Calendar")}>Create calendar</Button>
        {(admin.calendars.data ?? []).map((row) => <Text key={row.id} size="sm">
          {row.name} · {row.is_published ? "published" : "draft"} {row.is_current ? "· current" : ""}
          {!row.is_published && <Button ml="sm" size="xs" onClick={() => publish.mutate(row.id, {
            onError: (reason) => notifications.show({ color: "red", title: "Publish failed", message: errorMessage(reason) }),
          })}>Publish</Button>}
        </Text>)}
      </Stack></Paper>
      <Paper withBorder p="md"><Stack>
        <Text fw={600}>Task SLA</Text>
        <TextInput label="Task kind" value={taskKind} onChange={(event) => setTaskKind(event.currentTarget.value)} />
        <NumberInput label="Reminder after hours" value={reminderHours} onChange={setReminderHours} min={1} />
        <Button onClick={() => mutate(saveSla, { task_kind: taskKind, reminder_after_hours: reminderHours,
          escalation_after_hours: null, escalation_user_id: null }, "SLA configuration")}>Save SLA</Button>
        {(admin.sla.data ?? []).map((row) => <Text key={row.task_kind} size="sm">{row.task_kind}: reminder {row.reminder_after_hours}h</Text>)}
      </Stack></Paper>
      <Paper withBorder p="md"><Stack>
        <Text fw={600}>Record offline sanctioned leave</Text>
        <NumberInput label="Employee IAM user ID" value={employeeId} onChange={setEmployeeId} min={1} />
        <Select label="Leave category" data={leaveTypes()} value={leaveType} onChange={setLeaveType} />
        <TextInput label="Start date" type="date" value={offlineStart} onChange={(event) => setOfflineStart(event.currentTarget.value)} />
        <TextInput label="End date" type="date" value={offlineEnd} onChange={(event) => setOfflineEnd(event.currentTarget.value)} />
        <NumberInput label="Sanctioned leave days" value={offlineDays} onChange={setOfflineDays} min={0.5} decimalScale={2} />
        <TextInput label="Sanction evidence reference" value={sanctionReference} onChange={(event) => setSanctionReference(event.currentTarget.value)} />
        <Button disabled={!employeeId || !offlineStart || !offlineEnd || !sanctionReference}
          onClick={() => mutate(offlineLeave, { user_id: employeeId, leave_type: leaveType,
            start_date: offlineStart, end_date: offlineEnd, requested_days: offlineDays,
            sanction_reference: sanctionReference }, "Offline leave record")}>Record already-sanctioned leave</Button>
      </Stack></Paper>
      <Paper withBorder p="md"><Stack>
        <Text fw={600}>Maintain an authorized leave account record</Text>
        <NumberInput label="Employee IAM user ID" value={employeeId} onChange={setEmployeeId} min={1} />
        <Select label="Leave category" data={leaveTypes()} value={leaveType} onChange={setLeaveType} />
        <NumberInput label="Account adjustment (positive or negative)" value={adjustment} onChange={setAdjustment} decimalScale={2} />
        <TextInput label="Correction reason" value={adjustmentReason} onChange={(event) => setAdjustmentReason(event.currentTarget.value)} />
        <Button disabled={!employeeId || !adjustmentReason.trim()} onClick={() => mutate(correction,
          { user_id: employeeId, leave_type: leaveType, amount: adjustment,
            reason: adjustmentReason }, "Account correction")}>Record adjustment</Button>
      </Stack></Paper>
    </Stack>
  </Container>;
}
