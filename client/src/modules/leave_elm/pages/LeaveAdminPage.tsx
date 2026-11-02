import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  Alert, Button, Card, Checkbox, Container, Group, NumberInput, Select,
  Stack, Table, Text, TextInput, Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type Policy = {
  category: string;
  faculty_entitlement: string;
  staff_entitlement: string;
  faculty_eligible: boolean;
  staff_eligible: boolean;
  vacation_period_required: boolean;
  evidence_required: boolean;
  substitute_required: boolean;
  carry_forward: boolean;
  carry_forward_cap: string | null;
};

type Calendar = { id: number; name: string; year: number; is_published: boolean };
type Sla = {
  id: number;
  request_type: string;
  reminder_after_hours: number | null;
  escalation_after_hours: number | null;
  escalation_user_id: number | null;
  changes_assignment: boolean;
};

const categoryData = ["CL", "RH", "SCL", "EL", "COL", "VL"].map(
  (value) => ({ value, label: value }),
);
const requestTypes = ["leave", "extension", "cancellation", "offline", "resumption"].map(
  (value) => ({ value, label: value }),
);

function asText(value: string | number | null | undefined) {
  return value == null ? "" : String(value);
}

function dateString(value: Date | null) {
  if (!value) return "";
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${value.getFullYear()}-${month}-${day}`;
}

export default function LeaveAdminPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [calendars, setCalendars] = useState<Calendar[]>([]);
  const [sla, setSla] = useState<Sla[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [department, setDepartment] = useState("");
  const [hierarchyCategory, setHierarchyCategory] = useState<string | null>("CL");
  const [unitHeadId, setUnitHeadId] = useState<number | string>("");
  const [finalAuthorityId, setFinalAuthorityId] = useState<number | string>("");
  const [establishmentId, setEstablishmentId] = useState<number | string>("");
  const [calendarName, setCalendarName] = useState("");
  const [calendarYear, setCalendarYear] = useState<number | string>(new Date().getFullYear());
  const [holidayRows, setHolidayRows] = useState("");
  const [vacationYear, setVacationYear] = useState<number | string>(new Date().getFullYear());
  const [vacationStart, setVacationStart] = useState<Date | null>(null);
  const [vacationEnd, setVacationEnd] = useState<Date | null>(null);
  const [vacationReference, setVacationReference] = useState("");
  const [slaType, setSlaType] = useState<string | null>("leave");
  const [reminderHours, setReminderHours] = useState<number | string>("");
  const [escalationHours, setEscalationHours] = useState<number | string>("");
  const [escalationUserId, setEscalationUserId] = useState<number | string>("");
  const [changesAssignment, setChangesAssignment] = useState(false);
  const [offlineEmployee, setOfflineEmployee] = useState<number | string>("");
  const [offlineCategory, setOfflineCategory] = useState<string | null>("CL");
  const [offlineStart, setOfflineStart] = useState<Date | null>(null);
  const [offlineEnd, setOfflineEnd] = useState<Date | null>(null);
  const [offlineReason, setOfflineReason] = useState("");
  const [offlineEvidence, setOfflineEvidence] = useState("");
  const [yearEndYear, setYearEndYear] = useState<number | string>(new Date().getFullYear());
  const [yearEndMonth, setYearEndMonth] = useState<number | string>("");
  const [yearEndDay, setYearEndDay] = useState<number | string>("");

  const reload = useCallback(async () => {
    setError("");
    try {
      const [policyResponse, calendarResponse, slaResponse, yearEndResponse] = await Promise.all([
        http.get<Policy[]>("/leave/admin/policies"),
        http.get<Calendar[]>("/leave/admin/calendars"),
        http.get<Sla[]>("/leave/admin/sla"),
        http.get<{ month: number; day: number } | null>("/leave/admin/year-end-config"),
      ]);
      setPolicies(policyResponse.data);
      setCalendars(calendarResponse.data);
      setSla(slaResponse.data);
      setYearEndMonth(yearEndResponse.data?.month ?? "");
      setYearEndDay(yearEndResponse.data?.day ?? "");
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  async function savePolicy(policy: Policy) {
    setBusy(true);
    try {
      await http.put(`/leave/admin/policies/${policy.category}`, {
        faculty_entitlement: policy.faculty_entitlement,
        staff_entitlement: policy.staff_entitlement,
        faculty_eligible: policy.faculty_eligible,
        staff_eligible: policy.staff_eligible,
        vacation_period_required: policy.vacation_period_required,
        evidence_required: policy.evidence_required,
        substitute_required: policy.substitute_required,
        carry_forward: policy.carry_forward,
        carry_forward_cap: policy.carry_forward_cap || null,
      });
      notifications.show({ color: "green", title: "Policy saved", message: `${policy.category} updated.` });
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not save policy", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function saveHierarchy(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await http.post("/leave/admin/hierarchy", {
        department,
        category: hierarchyCategory,
        unit_head_user_id: Number(unitHeadId),
        final_authority_user_id: finalAuthorityId ? Number(finalAuthorityId) : null,
        establishment_user_id: establishmentId ? Number(establishmentId) : null,
      });
      notifications.show({ color: "green", title: "Routing saved", message: "Leave hierarchy updated." });
    } catch (e) {
      notifications.show({ color: "red", title: "Could not save routing", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function saveCalendar(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const dates = holidayRows.split("\n").filter(Boolean).map((line) => {
        const [date, label, restricted = "false", closed = "true"] =
          line.split("|").map((part) => part.trim());
        if (!date || !label) throw new Error("Each date row needs a date and label.");
        return {
          date, label,
          is_restricted: restricted.toLowerCase() === "true",
          is_closed: closed.toLowerCase() !== "false",
        };
      });
      await http.post("/leave/admin/calendars", {
        name: calendarName,
        year: Number(calendarYear),
        dates,
      });
      notifications.show({ color: "green", title: "Calendar created", message: "Publish it to make it effective." });
      setCalendarName("");
      setHolidayRows("");
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not create calendar", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function publishCalendar(id: number) {
    setBusy(true);
    try {
      await http.post(`/leave/admin/calendars/${id}/publish`);
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not publish calendar", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function saveVacation(event: FormEvent) {
    event.preventDefault();
    if (!vacationStart || !vacationEnd) return;
    setBusy(true);
    try {
      await http.post("/leave/admin/vacation-periods", {
        year: Number(vacationYear), start_date: dateString(vacationStart),
        end_date: dateString(vacationEnd), source_reference: vacationReference,
      });
      notifications.show({ color: "green", title: "Vacation period saved", message: "VL date source updated." });
    } catch (e) {
      notifications.show({ color: "red", title: "Could not save period", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function saveSla(event: FormEvent) {
    event.preventDefault();
    if (!slaType) return;
    setBusy(true);
    try {
      const current = sla.find((item) => item.request_type === slaType);
      const path = current ? `/leave/admin/sla/${current.id}` : "/leave/admin/sla";
      await http.put(path, {
        request_type: slaType,
        reminder_after_hours: reminderHours === "" ? null : Number(reminderHours),
        escalation_after_hours: escalationHours === "" ? null : Number(escalationHours),
        escalation_user_id: escalationUserId === "" ? null : Number(escalationUserId),
        changes_assignment: changesAssignment,
      });
      notifications.show({ color: "green", title: "SLA saved", message: "Thresholds are now configured." });
      await reload();
    } catch (e) {
      notifications.show({ color: "red", title: "Could not save SLA", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function recordOffline(event: FormEvent) {
    event.preventDefault();
    if (!offlineCategory || !offlineStart || !offlineEnd) return;
    setBusy(true);
    try {
      await http.post("/leave/admin/offline-leave", {
        employee_id: Number(offlineEmployee), category: offlineCategory,
        start_date: dateString(offlineStart), end_date: dateString(offlineEnd),
        reason: offlineReason, evidence_reference: offlineEvidence,
      });
      notifications.show({ color: "green", title: "Offline leave synchronized", message: "The balance and history were updated." });
    } catch (e) {
      notifications.show({ color: "red", title: "Could not record leave", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function runYearEnd() {
    setBusy(true);
    try {
      const response = await http.post<{ processed_employees: number }>(
        "/leave/admin/year-end", { year: Number(yearEndYear) },
      );
      notifications.show({
        color: "green", title: "Year-end processing complete",
        message: `${response.data.processed_employees} employee accounts processed.`,
      });
    } catch (e) {
      notifications.show({ color: "red", title: "Year-end processing failed", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function saveYearEndBoundary(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await http.put("/leave/admin/year-end-config", {
        month: Number(yearEndMonth), day: Number(yearEndDay),
      });
      notifications.show({
        color: "green", title: "Year-end boundary saved",
        message: "Year-end processing now follows the configured calendar boundary.",
      });
    } catch (e) {
      notifications.show({ color: "red", title: "Could not save boundary", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  async function processConfiguredYearEnd() {
    setBusy(true);
    try {
      const result = await http.post<{ due: boolean; processed_employees: number }>(
        "/leave/admin/process-year-end",
      );
      notifications.show({
        color: result.data.due ? "green" : "yellow",
        title: result.data.due ? "Year-end processed" : "Boundary not reached",
        message: result.data.due
          ? `${result.data.processed_employees} employee accounts processed.`
          : "No balances were changed.",
      });
    } catch (e) {
      notifications.show({ color: "red", title: "Year-end processing failed", message: errorMessage(e) });
    } finally {
      setBusy(false);
    }
  }

  function updatePolicy(category: string, patch: Partial<Policy>) {
    setPolicies((rows) => rows.map((row) =>
      row.category === category ? { ...row, ...patch } : row));
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Administration"
        subtitle="Maintain current policy, routing, calendars, and operational processing." />
      {error && <Alert color="red" mb="md">{error}</Alert>}
      <Stack>
        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Current leave policy</Text>
          <Table.ScrollContainer minWidth={1050}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Type</Table.Th><Table.Th>Faculty entitlement</Table.Th>
                  <Table.Th>Staff entitlement</Table.Th><Table.Th>Eligible</Table.Th>
                  <Table.Th>Options</Table.Th><Table.Th>Save</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {policies.map((policy) => (
                  <Table.Tr key={policy.category}>
                    <Table.Td>{policy.category}</Table.Td>
                    <Table.Td><NumberInput min={0} value={Number(policy.faculty_entitlement)}
                      onChange={(value) => updatePolicy(policy.category, {
                        faculty_entitlement: asText(value),
                      })} /></Table.Td>
                    <Table.Td><NumberInput min={0} value={Number(policy.staff_entitlement)}
                      onChange={(value) => updatePolicy(policy.category, {
                        staff_entitlement: asText(value),
                      })} /></Table.Td>
                    <Table.Td>
                      <Stack gap={4}>
                        <Checkbox label="Faculty" checked={policy.faculty_eligible}
                          onChange={(event) => updatePolicy(policy.category, {
                            faculty_eligible: event.currentTarget.checked,
                          })} />
                        <Checkbox label="Staff" checked={policy.staff_eligible}
                          onChange={(event) => updatePolicy(policy.category, {
                            staff_eligible: event.currentTarget.checked,
                          })} />
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Stack gap={4}>
                        <Checkbox label="Vacation period" checked={policy.vacation_period_required}
                          onChange={(event) => updatePolicy(policy.category, {
                            vacation_period_required: event.currentTarget.checked,
                          })} />
                        <Checkbox label="Evidence" checked={policy.evidence_required}
                          onChange={(event) => updatePolicy(policy.category, {
                            evidence_required: event.currentTarget.checked,
                          })} />
                        <Checkbox label="Substitute" checked={policy.substitute_required}
                          onChange={(event) => updatePolicy(policy.category, {
                            substitute_required: event.currentTarget.checked,
                          })} />
                        <Checkbox label="Carry forward" checked={policy.carry_forward}
                          onChange={(event) => updatePolicy(policy.category, {
                            carry_forward: event.currentTarget.checked,
                          })} />
                        {policy.carry_forward && (
                          <TextInput aria-label="Carry forward cap" placeholder="No cap"
                            value={policy.carry_forward_cap ?? ""}
                            onChange={(event) => updatePolicy(policy.category, {
                              carry_forward_cap: event.currentTarget.value || null,
                            })} />
                        )}
                      </Stack>
                    </Table.Td>
                    <Table.Td><Button size="xs" loading={busy}
                      onClick={() => void savePolicy(policy)}>Save</Button></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Approval hierarchy</Text>
          <form onSubmit={saveHierarchy}>
            <Stack>
              <Group grow>
                <TextInput label="Department / unit" value={department}
                  onChange={(event) => setDepartment(event.currentTarget.value)} required />
                <Select label="Leave category" data={categoryData}
                  value={hierarchyCategory} onChange={setHierarchyCategory} required />
                <NumberInput label="Unit Head Fusion user ID" min={1}
                  value={unitHeadId} onChange={setUnitHeadId} required />
              </Group>
              <Group grow>
                <NumberInput label="Final authority user ID (higher-sanction leave)" min={1}
                  value={finalAuthorityId} onChange={setFinalAuthorityId} />
                <NumberInput label="Establishment user ID (optional)" min={1}
                  value={establishmentId} onChange={setEstablishmentId} />
              </Group>
              <Button type="submit" loading={busy}>Save routing</Button>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Holiday and Restricted Holiday calendars</Text>
          <form onSubmit={saveCalendar}>
            <Stack>
              <Group grow>
                <TextInput label="Calendar name" value={calendarName}
                  onChange={(event) => setCalendarName(event.currentTarget.value)} required />
                <NumberInput label="Year" min={2000} max={2200}
                  value={calendarYear} onChange={setCalendarYear} required />
              </Group>
              <Textarea label="Dates (one per line: YYYY-MM-DD | label | restricted | closed)"
                description="Use true/false for restricted and closed; closed defaults to true."
                value={holidayRows} onChange={(event) => setHolidayRows(event.currentTarget.value)}
                minRows={3} required />
              <Button type="submit" loading={busy}>Create calendar</Button>
            </Stack>
          </form>
          <Table mt="md">
            <Table.Thead>
              <Table.Tr><Table.Th>Name</Table.Th><Table.Th>Year</Table.Th>
                <Table.Th>Status</Table.Th><Table.Th /></Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {calendars.map((calendar) => (
                <Table.Tr key={calendar.id}>
                  <Table.Td>{calendar.name}</Table.Td><Table.Td>{calendar.year}</Table.Td>
                  <Table.Td>{calendar.is_published ? "Published" : "Draft"}</Table.Td>
                  <Table.Td>{!calendar.is_published && (
                    <Button size="xs" loading={busy}
                      onClick={() => void publishCalendar(calendar.id)}>Publish</Button>
                  )}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Academic Calendar vacation periods</Text>
          <form onSubmit={saveVacation}>
            <Stack>
              <Group grow>
                <NumberInput label="Year" min={2000} max={2200}
                  value={vacationYear} onChange={setVacationYear} required />
                <DateInput label="Start date" value={vacationStart} onChange={setVacationStart} required />
                <DateInput label="End date" value={vacationEnd} onChange={setVacationEnd} required />
              </Group>
              <TextInput label="Academic Calendar source reference"
                value={vacationReference}
                onChange={(event) => setVacationReference(event.currentTarget.value)} />
              <Button type="submit" loading={busy}>Add vacation period</Button>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Workflow SLA thresholds</Text>
          <form onSubmit={saveSla}>
            <Stack>
              <Select label="Task type" data={requestTypes} value={slaType}
                onChange={(value) => {
                  setSlaType(value);
                  const found = sla.find((item) => item.request_type === value);
                  setReminderHours(found?.reminder_after_hours ?? "");
                  setEscalationHours(found?.escalation_after_hours ?? "");
                  setEscalationUserId(found?.escalation_user_id ?? "");
                  setChangesAssignment(found?.changes_assignment ?? false);
                }} />
              <Group grow>
                <NumberInput label="Reminder after hours" min={0} allowDecimal={false}
                  value={reminderHours} onChange={setReminderHours} />
                <NumberInput label="Escalation after hours" min={0} allowDecimal={false}
                  value={escalationHours} onChange={setEscalationHours} />
                <NumberInput label="Escalation authority user ID" min={1}
                  value={escalationUserId} onChange={setEscalationUserId} />
              </Group>
              <Checkbox label="Escalation changes task assignment"
                checked={changesAssignment}
                onChange={(event) => setChangesAssignment(event.currentTarget.checked)} />
              <Button type="submit" loading={busy}>Save SLA</Button>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Record already-sanctioned offline leave</Text>
          <form onSubmit={recordOffline}>
            <Stack>
              <Group grow>
                <NumberInput label="Employee Fusion user ID" min={1}
                  value={offlineEmployee} onChange={setOfflineEmployee} required />
                <Select label="Category" data={categoryData}
                  value={offlineCategory} onChange={setOfflineCategory} required />
                <DateInput label="Start date" value={offlineStart} onChange={setOfflineStart} required />
                <DateInput label="End date" value={offlineEnd} onChange={setOfflineEnd} required />
              </Group>
              <Textarea label="Reason" value={offlineReason}
                onChange={(event) => setOfflineReason(event.currentTarget.value)} required />
              <TextInput label="Sanction / evidence reference" value={offlineEvidence}
                onChange={(event) => setOfflineEvidence(event.currentTarget.value)} required />
              <Button type="submit" loading={busy}>Synchronize offline leave</Button>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Configured year-end boundary</Text>
          <form onSubmit={saveYearEndBoundary}>
            <Group align="flex-end">
              <NumberInput label="Month" min={1} max={12} value={yearEndMonth}
                onChange={setYearEndMonth} required />
              <NumberInput label="Day" min={1} max={31} value={yearEndDay}
                onChange={setYearEndDay} required />
              <Button type="submit" loading={busy}>Save boundary</Button>
              <Button variant="light" loading={busy}
                onClick={() => void processConfiguredYearEnd()}>
                Process if due today
              </Button>
            </Group>
          </form>
        </Card>

        <Card withBorder padding="lg">
          <Text fw={600} mb="sm">Manual year-end processing</Text>
          <Group align="flex-end">
            <NumberInput label="Target year" min={2000} max={2200}
              value={yearEndYear} onChange={setYearEndYear} />
            <Button loading={busy} onClick={() => void runYearEnd()}>
              Process year-end balances
            </Button>
          </Group>
        </Card>
      </Stack>
    </Container>
  );
}
