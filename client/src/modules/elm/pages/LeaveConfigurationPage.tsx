import { useState } from "react";
import {
  Alert, Button, Card, Checkbox, Grid, NumberInput, Select, Stack,
  Table, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import {
  type ApprovalRouteInput,
  type EmployeeProfileInput,
  type OrganizationUnitInput,
} from "../api";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateApprovalRoute, useCreateCalendarDate, useCreateEmployeeProfile,
  useCreateOrganizationUnit, useLeaveCalendar, useLeavePolicies,
  usePublishCalendarDate, useUpdateLeavePolicy, useAdjustLeaveAccount,
  useRecordOfflineLeave,
} from "../hooks/useLeaveManagement";
import { useElmRole } from "../hooks/useRole";
import type { LeavePolicy } from "../types";

const categories = ["CL", "RH", "SCL", "EL", "COL", "VL"];

export default function LeaveConfigurationPage() {
  const role = useElmRole();
  const policies = useLeavePolicies();
  const calendar = useLeaveCalendar();
  const updatePolicy = useUpdateLeavePolicy();
  const createDate = useCreateCalendarDate();
  const publishDate = usePublishCalendarDate();
  const createUnit = useCreateOrganizationUnit();
  const createProfile = useCreateEmployeeProfile();
  const createRoute = useCreateApprovalRoute();
  const recordLeave = useRecordOfflineLeave();
  const adjustAccount = useAdjustLeaveAccount();
  const [drafts, setDrafts] = useState<Record<string, Partial<LeavePolicy>>>({});
  const [error, setError] = useState("");
  const [calendarDate, setCalendarDate] = useState("");
  const [calendarKind, setCalendarKind] = useState<string | null>(null);
  const [calendarLabel, setCalendarLabel] = useState("");
  const [unit, setUnit] = useState({ code: "", name: "", head: "" });
  const [profile, setProfile] = useState({
    userId: "", employeeType: "staff", designation: "", organizationUnit: "",
  });
  const [route, setRoute] = useState({
    category: "CL", organizationUnit: "", approverUserId: "", approverRole: "",
    establishmentRequired: false,
  });
  const [offline, setOffline] = useState({
    userId: "", category: "CL", start: "", end: "", halfDay: "none", purpose: "",
  });
  const [adjustment, setAdjustment] = useState({
    userId: "", category: "CL", year: String(new Date().getFullYear()),
    amount: "", description: "",
  });

  const save = async (action: () => Promise<unknown>, success: string) => {
    try {
      await action();
      setError("");
      notifications.show({ color: "green", title: "Saved", message: success });
    } catch (reason) {
      setError(errorMessage(reason));
    }
  };
  if (policies.error || calendar.error) {
    return <div><ErrorState error={policies.error ?? calendar.error} /></div>;
  }

  const policyMutation = (policy: LeavePolicy) => {
    const data = { ...policy, ...drafts[policy.category] };
    return save(async () => {
      await updatePolicy.mutateAsync({ category: policy.category, body: data });
      setDrafts((old) => {
        const next = { ...old };
        delete next[policy.category];
        return next;
      });
    }, `${policy.category} policy was updated.`);
  };

  const submitCalendarDate = () => {
    if (!calendarDate || !calendarKind) return;
    void save(() => createDate.mutateAsync({
      date: calendarDate, kind: calendarKind, label: calendarLabel,
    }), "Calendar entry saved as unpublished.");
  };

  return (
    <Stack>
      <PageHeader
        title="ELM Configuration"
        subtitle="Maintain current policy, employee routing and published leave calendars"
      />
      {error && <Alert color="red" title="Configuration update failed">{error}</Alert>}
      {role.canManage && (
        <>
          <Card withBorder>
            <Text fw={600} mb="sm">Leave policies</Text>
            {policies.isPending ? <Text c="dimmed">Loading policies…</Text> : (
              <Table.ScrollContainer minWidth={960}>
                <Table>
                  <Table.Thead><Table.Tr>
                    <Table.Th>Category</Table.Th><Table.Th>Annual days</Table.Th>
                    <Table.Th>Faculty only</Table.Th><Table.Th>Continuous</Table.Th>
                    <Table.Th>Carry forward</Table.Th><Table.Th>Half-day CL</Table.Th>
                    <Table.Th>Medical evidence</Table.Th><Table.Th />
                  </Table.Tr></Table.Thead>
                  <Table.Tbody>
                    {(policies.data ?? []).map((policy) => {
                      const value = { ...policy, ...drafts[policy.category] };
                      return (
                        <Table.Tr key={policy.category}>
                          <Table.Td>{policy.category}</Table.Td>
                          <Table.Td>
                            <NumberInput w={100} min={0} decimalScale={2}
                              value={value.annual_entitlement}
                              onChange={(n) => setDrafts((old) => ({
                                ...old, [policy.category]: {
                                  ...old[policy.category], annual_entitlement: String(n),
                                },
                              }))} />
                          </Table.Td>
                          {([
                            ["faculty_only", value.faculty_only],
                            ["continuous_days", value.continuous_days],
                            ["carry_forward", value.carry_forward],
                            ["allow_half_day", value.allow_half_day],
                            ["medical_evidence_required", value.medical_evidence_required],
                          ] as const).map(([field, checked]) => (
                            <Table.Td key={field}>
                              <Checkbox checked={checked}
                                onChange={(event) => setDrafts((old) => ({
                                  ...old, [policy.category]: {
                                    ...old[policy.category], [field]: event.currentTarget.checked,
                                  },
                                }))} />
                            </Table.Td>
                          ))}
                          <Table.Td>
                            <Button size="xs" loading={updatePolicy.isPending}
                              onClick={() => void policyMutation(policy)}>Save</Button>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
          </Card>
          <Card withBorder>
            <Text fw={600} mb="sm">Organization unit and Unit Head</Text>
            <Grid align="flex-end">
              <Grid.Col span={{ base: 12, sm: 4 }}>
                <TextInput label="Unit code" value={unit.code}
                  onChange={(e) => setUnit({ ...unit, code: e.currentTarget.value })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 4 }}>
                <TextInput label="Unit name" value={unit.name}
                  onChange={(e) => setUnit({ ...unit, name: e.currentTarget.value })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 3 }}>
                <NumberInput label="Unit Head employee ID" min={1} value={unit.head}
                  onChange={(v) => setUnit({ ...unit, head: String(v || "") })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 1 }}>
                <Button fullWidth loading={createUnit.isPending}
                  disabled={!unit.code.trim() || !unit.name.trim()}
                  onClick={() => void save(() => createUnit.mutateAsync({
                    code: unit.code.trim(), name: unit.name.trim(),
                    unit_head_user_id: unit.head ? Number(unit.head) : null,
                    is_active: true,
                  } satisfies OrganizationUnitInput), "Organization unit saved.")}>
                  Add
                </Button>
              </Grid.Col>
            </Grid>
          </Card>
          <Card withBorder>
            <Text fw={600} mb="sm">Employee ELM profile</Text>
            <Grid align="flex-end">
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <NumberInput label="Employee ID" min={1} value={profile.userId}
                  onChange={(v) => setProfile({ ...profile, userId: String(v || "") })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <Select label="Employee type" value={profile.employeeType}
                  data={["faculty", "staff"]}
                  onChange={(v) => setProfile({
                    ...profile, employeeType: v ?? "staff",
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 3 }}>
                <TextInput label="Designation" value={profile.designation}
                  onChange={(e) => setProfile({
                    ...profile, designation: e.currentTarget.value,
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <NumberInput label="Organization unit ID" min={1}
                  value={profile.organizationUnit}
                  onChange={(v) => setProfile({
                    ...profile, organizationUnit: String(v || ""),
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 3 }}>
                <Button fullWidth loading={createProfile.isPending}
                  disabled={!profile.userId}
                  onClick={() => void save(() => createProfile.mutateAsync({
                    user_id: Number(profile.userId),
                    employee_type: profile.employeeType as EmployeeProfileInput["employee_type"],
                    designation: profile.designation.trim(),
                    organization_unit: profile.organizationUnit
                      ? Number(profile.organizationUnit) : null,
                    is_active: true,
                  } satisfies EmployeeProfileInput), "Employee profile saved.")}>
                  Save employee profile
                </Button>
              </Grid.Col>
            </Grid>
          </Card>
          <Card withBorder>
            <Text fw={600} mb="sm">Final sanction route</Text>
            <Grid align="flex-end">
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <Select label="Leave category" data={categories}
                  value={route.category} onChange={(v) => setRoute({
                    ...route, category: v ?? "CL",
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <NumberInput label="Unit ID (blank for default)" min={1}
                  value={route.organizationUnit}
                  onChange={(v) => setRoute({
                    ...route, organizationUnit: String(v || ""),
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <NumberInput label="Approver employee ID (optional)" min={1}
                  value={route.approverUserId}
                  onChange={(v) => setRoute({
                    ...route, approverUserId: String(v || ""),
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <TextInput label="Approver role label" value={route.approverRole}
                  onChange={(e) => setRoute({
                    ...route, approverRole: e.currentTarget.value,
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <Checkbox label="Establishment verification required"
                  checked={route.establishmentRequired}
                  onChange={(e) => setRoute({
                    ...route, establishmentRequired: e.currentTarget.checked,
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <Button fullWidth loading={createRoute.isPending}
                  onClick={() => void save(() => createRoute.mutateAsync({
                    category: route.category,
                    organization_unit: route.organizationUnit
                      ? Number(route.organizationUnit) : null,
                    approver_user_id: route.approverUserId
                      ? Number(route.approverUserId) : null,
                    approver_role: route.approverRole.trim(),
                    permission_code: "elm.leave.sanction",
                    establishment_required: route.establishmentRequired,
                    is_active: true,
                  } satisfies ApprovalRouteInput), "Sanction route saved.")}>
                  Save route
                </Button>
              </Grid.Col>
            </Grid>
          </Card>
        </>
      )}
      {role.canManageRecords && (
        <>
          <Card withBorder>
            <Text fw={600} mb="sm">Record already-sanctioned offline leave</Text>
            <Grid align="flex-end">
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <NumberInput label="Employee ID" min={1} value={offline.userId}
                  onChange={(v) => setOffline({ ...offline, userId: String(v || "") })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <Select label="Category" data={categories} value={offline.category}
                  onChange={(v) => setOffline({ ...offline, category: v ?? "CL" })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <TextInput type="date" label="From" value={offline.start}
                  onChange={(e) => setOffline({ ...offline, start: e.currentTarget.value })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <TextInput type="date" label="To" value={offline.end}
                  onChange={(e) => setOffline({ ...offline, end: e.currentTarget.value })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <Select label="CL period" data={[
                  { value: "none", label: "Full day" },
                  { value: "first_half", label: "First half" },
                  { value: "second_half", label: "Second half" },
                ]} value={offline.halfDay}
                onChange={(v) => setOffline({ ...offline, halfDay: v ?? "none" })}
                disabled={offline.category !== "CL"} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <Button fullWidth loading={recordLeave.isPending}
                  disabled={!offline.userId || !offline.start || !offline.end
                    || !offline.purpose.trim()}
                  onClick={() => void save(() => recordLeave.mutateAsync({
                    user_id: Number(offline.userId), category: offline.category,
                    start_date: offline.start, end_date: offline.end,
                    half_day: offline.halfDay, purpose: offline.purpose.trim(),
                  }), "Offline-sanctioned leave recorded.")}>
                  Record leave
                </Button>
              </Grid.Col>
              <Grid.Col span={12}>
                <TextInput label="Sanction / record reference" value={offline.purpose}
                  onChange={(e) => setOffline({ ...offline, purpose: e.currentTarget.value })} />
              </Grid.Col>
            </Grid>
          </Card>
          <Card withBorder>
            <Text fw={600} mb="sm">Adjust a leave account</Text>
            <Grid align="flex-end">
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <NumberInput label="Employee ID" min={1} value={adjustment.userId}
                  onChange={(v) => setAdjustment({ ...adjustment, userId: String(v || "") })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <Select label="Category" data={categories} value={adjustment.category}
                  onChange={(v) => setAdjustment({ ...adjustment, category: v ?? "CL" })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <NumberInput label="Account year" min={2000} max={2100}
                  value={adjustment.year}
                  onChange={(v) => setAdjustment({ ...adjustment, year: String(v || "") })} />
              </Grid.Col>
              <Grid.Col span={{ base: 6, sm: 2 }}>
                <TextInput label="Adjustment (+/- days)" type="number" step="0.5"
                  value={adjustment.amount}
                  onChange={(e) => setAdjustment({
                    ...adjustment, amount: e.currentTarget.value,
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <TextInput label="Reason" value={adjustment.description}
                  onChange={(e) => setAdjustment({
                    ...adjustment, description: e.currentTarget.value,
                  })} />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 2 }}>
                <Button fullWidth loading={adjustAccount.isPending}
                  disabled={!adjustment.userId || !adjustment.amount
                    || !adjustment.description.trim()}
                  onClick={() => void save(() => adjustAccount.mutateAsync({
                    user_id: Number(adjustment.userId),
                    category: adjustment.category,
                    year: Number(adjustment.year),
                    amount: adjustment.amount,
                    description: adjustment.description.trim(),
                  }), "Account adjustment recorded.")}>
                  Adjust balance
                </Button>
              </Grid.Col>
            </Grid>
          </Card>
        </>
      )}
      {role.canManageCalendar && (
        <Card withBorder>
          <Text fw={600} mb="sm">Holiday and vacation calendar</Text>
          <Grid align="flex-end">
            <Grid.Col span={{ base: 12, sm: 3 }}>
              <TextInput type="date" label="Date" value={calendarDate}
                onChange={(e) => setCalendarDate(e.currentTarget.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 3 }}>
              <Select label="Calendar entry type" value={calendarKind}
                data={[
                  { value: "restricted_holiday", label: "Restricted Holiday" },
                  { value: "closed_holiday", label: "Closed Holiday" },
                  { value: "vacation", label: "Vacation day" },
                ]}
                onChange={setCalendarKind} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 4 }}>
              <TextInput label="Label" value={calendarLabel}
                onChange={(e) => setCalendarLabel(e.currentTarget.value)} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 2 }}>
              <Button fullWidth loading={createDate.isPending}
                onClick={submitCalendarDate}>Add date</Button>
            </Grid.Col>
          </Grid>
          <Table mt="md">
            <Table.Thead><Table.Tr>
              <Table.Th>Date</Table.Th><Table.Th>Type</Table.Th>
              <Table.Th>Label</Table.Th><Table.Th>Published</Table.Th><Table.Th />
            </Table.Tr></Table.Thead>
            <Table.Tbody>
              {(calendar.data ?? []).map((entry) => (
                <Table.Tr key={entry.id}>
                  <Table.Td>{entry.date}</Table.Td>
                  <Table.Td>{entry.kind.replaceAll("_", " ")}</Table.Td>
                  <Table.Td>{entry.label}</Table.Td>
                  <Table.Td>{entry.is_published ? "Yes" : "No"}</Table.Td>
                  <Table.Td>{!entry.is_published && (
                    <Button size="xs" variant="light" loading={publishDate.isPending}
                      onClick={() => void save(
                        () => publishDate.mutateAsync(entry.id),
                        "Calendar entry is now effective.")}>
                      Publish
                    </Button>
                  )}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}
