import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Grid,
  Group,
  Select,
  Stack,
  TextInput,
  Title,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";

export default function AdminPage() {
  const [loading, setLoading] = useState(false);
  const [employeeId, setEmployeeId] = useState("");
  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [daysCount, setDaysCount] = useState("1.0");
  const [referenceNo, setReferenceNo] = useState("");
  const [sanctionDate, setSanctionDate] = useState("");
  const [purpose, setPurpose] = useState("");
  const [routeCategory, setRouteCategory] = useState<string | null>("CL");
  const [routeDepartment, setRouteDepartment] = useState("");
  const [routeRole, setRouteRole] = useState("");
  const [routeJson, setRouteJson] = useState('{"unit_head_user_id": 101}');
  const [entitlementJson, setEntitlementJson] = useState('{"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "VL": 60, "COL": 20}');
  const [reminderHours, setReminderHours] = useState("24");
  const [escalationHours, setEscalationHours] = useState("72");
  const [escalationUserId, setEscalationUserId] = useState("");
  const [holidayName, setHolidayName] = useState("");
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayKind, setHolidayKind] = useState<string | null>("closed");
  const [draftHolidayIds, setDraftHolidayIds] = useState<number[]>([]);
  const [correctionId, setCorrectionId] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [correctionPurpose, setCorrectionPurpose] = useState("");

  const saveCorrection = async () => {
    if (!correctionId || !correctionReason.trim() || !correctionPurpose.trim()) return;
    try {
      await leaveApi.maintainRecord(Number(correctionId), {
        reason: correctionReason.trim(), purpose: correctionPurpose.trim(),
      });
      notifications.show({ title: "Record corrected", message: "Correction was recorded in the audit history.", color: "teal" });
      setCorrectionReason("");
      setCorrectionPurpose("");
    } catch (err) {
      notifications.show({ title: "Correction failed", message: errorMessage(err), color: "red" });
    }
  };

  const saveRoute = async () => {
    if (!routeCategory) return;
    try {
      const routeKey = `route.${routeCategory}${routeDepartment.trim() ? `.${routeDepartment.trim()}` : ""}${routeRole.trim() ? `.${routeRole.trim().toLowerCase().replaceAll(" ", "_")}` : ""}`;
      await leaveApi.saveConfig(routeKey, JSON.parse(routeJson), "Current approver assignment for this leave category and department.");
      notifications.show({ title: "Route saved", message: `Approvers configured for ${routeCategory}.`, color: "teal" });
    } catch (err) {
      notifications.show({ title: "Configuration error", message: err instanceof SyntaxError ? "Enter valid JSON." : errorMessage(err), color: "red" });
    }
  };

  const saveSla = async () => {
    try {
      await leaveApi.saveConfig("sla.reminder_hours", Number(reminderHours));
      await leaveApi.saveConfig("sla.escalation_hours", Number(escalationHours));
      if (escalationUserId.trim()) {
        await leaveApi.saveConfig("sla.escalation_user_id", Number(escalationUserId));
      }
      notifications.show({ title: "SLA thresholds saved", message: "Thresholds apply to the next scheduled SLA run.", color: "teal" });
    } catch (err) {
      notifications.show({ title: "Configuration error", message: errorMessage(err), color: "red" });
    }
  };

  const saveEntitlements = async () => {
    try {
      await leaveApi.saveConfig("policy.entitlements", JSON.parse(entitlementJson), "Current annual category entitlements in days.");
      notifications.show({ title: "Policy saved", message: "New balances and year-end grants will use these current values.", color: "teal" });
    } catch (err) {
      notifications.show({ title: "Policy error", message: err instanceof SyntaxError ? "Enter valid JSON." : errorMessage(err), color: "red" });
    }
  };

  const addHoliday = async () => {
    if (!holidayName.trim() || !holidayDate || !holidayKind) return;
    try {
      const year = Number(holidayDate.slice(0, 4));
      const rows = await leaveApi.addCalendarEntries(year, [{ name: holidayName.trim(), date: holidayDate, kind: holidayKind as "closed" | "restricted" }]);
      setDraftHolidayIds((ids) => [...ids, ...rows.map((row) => row.id)]);
      setHolidayName("");
      notifications.show({ title: "Calendar draft saved", message: "Publish the draft year to make it effective.", color: "blue" });
    } catch (err) {
      notifications.show({ title: "Calendar error", message: errorMessage(err), color: "red" });
    }
  };

  const publishHoliday = async () => {
    if (!holidayDate || !draftHolidayIds.length) return;
    try {
      await leaveApi.publishCalendar(Number(holidayDate.slice(0, 4)), draftHolidayIds);
      setDraftHolidayIds([]);
      notifications.show({ title: "Calendar published", message: "The new calendar is now effective.", color: "teal" });
    } catch (err) {
      notifications.show({ title: "Calendar error", message: errorMessage(err), color: "red" });
    }
  };

  const handleOfflineSync = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId || !category || !startDate || !endDate || !referenceNo || !sanctionDate) {
      notifications.show({ title: "Error", message: "Please fill in all required fields.", color: "red" });
      return;
    }

    try {
      setLoading(true);
      await leaveApi.recordOfflineSync({
        employee_user_id: parseInt(employeeId, 10),
        category,
        start_date: startDate,
        end_date: endDate,
        days_count: parseFloat(daysCount),
        offline_reference_no: referenceNo.trim(),
        offline_sanction_date: sanctionDate,
        purpose: purpose.trim(),
      });

      notifications.show({
        title: "Synchronized",
        message: "Offline sanction successfully recorded and balance updated.",
        color: "teal",
      });

      setReferenceNo("");
      setPurpose("");
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Leave Administration"
        subtitle="Record already-sanctioned offline leave and administrative record synchronization."
      />

      <Card padding="xl" shadow="sm" radius="md" withBorder>
        <Title order={4} mb="xs">Record Offline-Sanctioned Leave (BR-EL-029, EL-UC-016)</Title>
        <Text size="xs" c="dimmed" mb="lg">
          For leaves approved via paper orders when the portal could not be used. Updates leave account and balance directly.
        </Text>

        <form onSubmit={handleOfflineSync}>
          <Stack gap="md">
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="number"
                  label="Employee User ID"
                  placeholder="e.g. 101"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Category"
                  data={[
                    { value: "CL", label: "Casual Leave (CL)" },
                    { value: "RH", label: "Restricted Holiday (RH)" },
                    { value: "SCL", label: "Special Casual Leave (SCL)" },
                    { value: "EL", label: "Earned Leave (EL)" },
                    { value: "VL", label: "Vacation Leave (VL)" },
                    { value: "COL", label: "Commuted Leave (COL)" },
                  ]}
                  value={category}
                  onChange={setCategory}
                  required
                />
              </Grid.Col>
            </Grid>

            <Grid>
              <Grid.Col span={{ base: 12, sm: 4 }}>
                <TextInput
                  type="date"
                  label="Start Date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 4 }}>
                <TextInput
                  type="date"
                  label="End Date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 4 }}>
                <TextInput
                  type="number"
                  step="0.5"
                  label="Deductible Days"
                  value={daysCount}
                  onChange={(e) => setDaysCount(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
            </Grid>

            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Offline Order / Reference No."
                  placeholder="e.g. EST/2026/L-441"
                  value={referenceNo}
                  onChange={(e) => setReferenceNo(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="Order / Sanction Date"
                  value={sanctionDate}
                  onChange={(e) => setSanctionDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
            </Grid>

            <TextInput
              label="Purpose / Remarks"
              placeholder="e.g. Approved medical leave with certificate"
              value={purpose}
              onChange={(e) => setPurpose(e.currentTarget.value)}
            />

            <Button type="submit" loading={loading} mt="md">
              Synchronize Offline Record
            </Button>
          </Stack>
        </form>
      </Card>

      <Card mt="lg" padding="xl" shadow="sm" radius="md" withBorder>
        <Title order={4} mb="xs">Maintain Finalized Leave Record</Title>
        <Text size="xs" c="dimmed" mb="md">Correct descriptive details on a finalized record. Each change is audited and does not change the sanction or leave balance.</Text>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 4 }}><TextInput type="number" label="Application ID" value={correctionId} onChange={(e) => setCorrectionId(e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, sm: 8 }}><TextInput label="Correction reason" value={correctionReason} onChange={(e) => setCorrectionReason(e.currentTarget.value)} /></Grid.Col>
        </Grid>
        <Textarea mt="md" label="Corrected purpose" value={correctionPurpose} onChange={(e) => setCorrectionPurpose(e.currentTarget.value)} />
        <Button mt="md" onClick={saveCorrection}>Save Correction</Button>
      </Card>

      <Card mt="lg" padding="xl" shadow="sm" radius="md" withBorder>
        <Title order={4} mb="xs">Approver Route Configuration</Title>
        <Text size="xs" c="dimmed" mb="md">Use employee user IDs. A department-and-role route overrides the department route, which overrides the category route. CL/RH require a Unit Head; SCL/EL/COL/VL also require a sanctioning authority. Establishment is optional.</Text>
        <Stack>
          <Select label="Leave category" data={["CL", "RH", "SCL", "EL", "COL", "VL"]} value={routeCategory} onChange={setRouteCategory} />
          <TextInput label="Department (optional)" value={routeDepartment} onChange={(e) => setRouteDepartment(e.currentTarget.value)} />
          <TextInput label="Role (optional; spaces become underscores)" value={routeRole} onChange={(e) => setRouteRole(e.currentTarget.value)} />
          <Textarea label="Route JSON" minRows={3} value={routeJson} onChange={(e) => setRouteJson(e.currentTarget.value)} />
          <Button onClick={saveRoute}>Save Route</Button>
        </Stack>
      </Card>

      <Card mt="lg" padding="xl" shadow="sm" radius="md" withBorder>
        <Title order={4} mb="xs">Leave Entitlements</Title>
        <Text size="xs" c="dimmed" mb="md">Current category entitlement values in days. Faculty EL annual grant is excluded; faculty VL uses the configured VL value.</Text>
        <Textarea label="Entitlements JSON" minRows={3} value={entitlementJson} onChange={(e) => setEntitlementJson(e.currentTarget.value)} />
        <Button mt="md" onClick={saveEntitlements}>Save Policy</Button>
      </Card>

      <Card mt="lg" padding="xl" shadow="sm" radius="md" withBorder>
        <Title order={4} mb="xs">Workflow SLA Thresholds</Title>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6 }}><TextInput type="number" min={1} label="Reminder after (hours)" value={reminderHours} onChange={(e) => setReminderHours(e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6 }}><TextInput type="number" min={1} label="Escalate after (hours)" value={escalationHours} onChange={(e) => setEscalationHours(e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6 }}><TextInput type="number" min={1} label="Escalation authority user ID (optional)" value={escalationUserId} onChange={(e) => setEscalationUserId(e.currentTarget.value)} /></Grid.Col>
        </Grid>
        <Button mt="md" onClick={saveSla}>Save SLA Thresholds</Button>
      </Card>

      <Card mt="lg" padding="xl" shadow="sm" radius="md" withBorder>
        <Title order={4} mb="xs">Holiday / Restricted Holiday Calendar</Title>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 4 }}><TextInput label="Name" value={holidayName} onChange={(e) => setHolidayName(e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}><TextInput type="date" label="Date" value={holidayDate} onChange={(e) => setHolidayDate(e.currentTarget.value)} /></Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}><Select label="Kind" data={[{ value: "closed", label: "Closed holiday" }, { value: "restricted", label: "Restricted holiday" }]} value={holidayKind} onChange={setHolidayKind} /></Grid.Col>
        </Grid>
        <Group mt="md">
          <Button variant="light" onClick={addHoliday}>Add to Draft</Button>
          <Button color="teal" disabled={!draftHolidayIds.length} onClick={publishHoliday}>Publish {draftHolidayIds.length} Draft Entry(s)</Button>
        </Group>
      </Card>
    </Container>
  );
}
