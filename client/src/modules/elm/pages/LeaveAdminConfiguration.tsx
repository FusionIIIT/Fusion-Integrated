import {
  Alert, Button, Card, Checkbox, Group, NumberInput, Select, Stack, Text,
  TextInput, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import {
  useApprovalRoutes, useCreateApprovalRoute, useCreateHoliday,
  useCreateHolidayCalendar, useCreateLeavePolicy, useCreateOrgUnit,
  useCreateVacationPeriod, useHolidayCalendars, useMaintainEmployeeProfile,
  useMaintainLeaveRecord, useOrgUnits, usePublishHolidayCalendar,
} from "../api/hooks";
import type { HolidayCalendar } from "../api/types";

const CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"];

function isRouteStep(value: unknown): value is { user_id: number; role: string } {
  if (typeof value !== "object" || value === null) return false;
  const step = value as Record<string, unknown>;
  return Number.isInteger(step.user_id) && Number(step.user_id) > 0
    && typeof step.role === "string" && Boolean(step.role.trim());
}

export default function LeaveAdminConfiguration() {
  const { can } = useAuth();
  const canManagePolicy = can("employee_leave.policy.manage");
  const canManageCalendar = can("employee_leave.calendar.manage");
  const canManageEmployee = can("employee_leave.employee.manage");
  const units = useOrgUnits(canManageEmployee);
  const calendars = useHolidayCalendars(canManageCalendar);
  const routes = useApprovalRoutes(canManagePolicy);
  const createPolicy = useCreateLeavePolicy();
  const createUnit = useCreateOrgUnit();
  const createRoute = useCreateApprovalRoute();
  const createCalendar = useCreateHolidayCalendar();
  const maintainProfile = useMaintainEmployeeProfile();
  const maintainRecord = useMaintainLeaveRecord();
  const createVacation = useCreateVacationPeriod();
  const publishCalendar = usePublishHolidayCalendar();
  const [policyYear, setPolicyYear] = useState<number | string>("");
  const [unitCode, setUnitCode] = useState("");
  const [unitName, setUnitName] = useState("");
  const [unitHead, setUnitHead] = useState<number | string>("");
  const [routeCategory, setRouteCategory] = useState<string | null>("EL");
  const [routeUnit, setRouteUnit] = useState<string | null>(null);
  const [routeDesignation, setRouteDesignation] = useState("");
  const [routeSteps, setRouteSteps] = useState('[{"user_id": 1, "role": "Registrar"}]');
  const [calendarYear, setCalendarYear] = useState<number | string>("");
  const [calendarName, setCalendarName] = useState("");
  const [selectedCalendar, setSelectedCalendar] = useState<string | null>(null);
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayName, setHolidayName] = useState("");
  const [holidayKind, setHolidayKind] = useState<string | null>("closed");
  const [vacationAcademicYear, setVacationAcademicYear] = useState("");
  const [vacationLabel, setVacationLabel] = useState("");
  const [vacationStartsOn, setVacationStartsOn] = useState("");
  const [vacationEndsOn, setVacationEndsOn] = useState("");
  const [profileUser, setProfileUser] = useState<number | string>("");
  const [profileKind, setProfileKind] = useState<string | null>("staff");
  const [profileUnit, setProfileUnit] = useState<string | null>(null);
  const [designation, setDesignation] = useState("");
  const [requiresSubstitute, setRequiresSubstitute] = useState(false);
  const [isDirector, setIsDirector] = useState(false);
  const [recordId, setRecordId] = useState<number | string>("");
  const [maintenanceReason, setMaintenanceReason] = useState("");
  const [correctedPurpose, setCorrectedPurpose] = useState("");
  const [correctedReference, setCorrectedReference] = useState("");

  const fail = (error: unknown) =>
    notifications.show({ color: "red", message: errorMessage(error) });
  const success = (message: string) =>
    notifications.show({ message });
  const parsedSteps = () => {
    try {
      const value: unknown = JSON.parse(routeSteps);
      if (!Array.isArray(value) || !value.every(isRouteStep)) {
        throw new Error("Each approval step needs a positive user_id and non-empty role.");
      }
      return value;
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : "Invalid approval-step JSON.");
    }
  };
  const selectedCalendarValue: HolidayCalendar | undefined = calendars.data?.results.find(
    (item) => String(item.id) === selectedCalendar,
  );
  const addHoliday = useCreateHoliday(Number(selectedCalendar ?? 0));

  const configurationError = units.isError || calendars.isError || routes.isError;
  const configurationErrorValue = units.error ?? calendars.error ?? routes.error;

  return (
    <Stack>
      <Title order={3}>ELM configuration</Title>
      {configurationError && (
        <Alert color="red" title="Unable to load ELM configuration">
          {errorMessage(configurationErrorValue)}
        </Alert>
      )}
      {canManagePolicy && (
        <>
          <Card withBorder>
            <Stack>
              <Title order={4}>Create annual leave policy</Title>
              <Text size="sm">
                Policy values take effect immediately for their calendar year.
              </Text>
              <NumberInput
                label="Calendar year"
                min={1900}
                max={9999}
                value={policyYear}
                onChange={setPolicyYear}
              />
              <Button
                disabled={!Number.isInteger(Number(policyYear)) || Number(policyYear) < 1900}
                loading={createPolicy.isPending}
                onClick={() => createPolicy.mutate({
                  year: Number(policyYear),
                  reminder_after_hours: 48,
                  escalate_after_hours: 96,
                }, {
                  onError: fail,
                  onSuccess: () => success("Annual leave policy created."),
                })}
              >
                Create policy with default entitlements
              </Button>
            </Stack>
          </Card>
          <Card withBorder>
            <Stack>
              <Title order={4}>Approval route</Title>
              <Text size="sm">
                Use a JSON array of ordered steps with a positive user_id and role.
              </Text>
              <Select
                label="Leave category"
                data={CATEGORIES}
                value={routeCategory}
                onChange={setRouteCategory}
              />
              <Select
                label="Organizational unit (optional global fallback)"
                clearable
                data={(units.data?.results ?? []).map((unit) => ({
                  value: String(unit.id), label: unit.name,
                }))}
                value={routeUnit}
                onChange={setRouteUnit}
              />
              <TextInput
                label="Designation (optional)"
                value={routeDesignation}
                onChange={(event) => setRouteDesignation(event.currentTarget.value)}
              />
              <Textarea
                label="Ordered approval steps"
                minRows={3}
                value={routeSteps}
                onChange={(event) => setRouteSteps(event.currentTarget.value)}
              />
              <Button
                disabled={!routeCategory}
                loading={createRoute.isPending}
                onClick={() => {
                  try {
                    createRoute.mutate({
                      category: routeCategory ?? "",
                      unit_id: routeUnit ? Number(routeUnit) : null,
                      designation: routeDesignation,
                      steps: parsedSteps(),
                      is_active: true,
                    }, {
                      onError: fail,
                      onSuccess: () => success("Approval route created."),
                    });
                  } catch (error) {
                    fail(error);
                  }
                }}
              >
                Create approval route
              </Button>
              {(routes.data?.results ?? []).map((route) => (
                <Text key={route.id} size="sm">
                  {route.category} · {route.designation || "all designations"} ·
                  {" "}{route.steps.length} step(s)
                </Text>
              ))}
            </Stack>
          </Card>
        </>
      )}
      {canManageCalendar && (
        <>
        <Card withBorder>
          <Stack>
            <Title order={4}>Holiday calendars</Title>
            <Group grow>
              <NumberInput
                label="Calendar year"
                min={1900}
                value={calendarYear}
                onChange={setCalendarYear}
              />
              <TextInput
                label="Calendar name"
                value={calendarName}
                onChange={(event) => setCalendarName(event.currentTarget.value)}
              />
            </Group>
            <Button
              disabled={!Number.isInteger(Number(calendarYear)) || !calendarName.trim()}
              loading={createCalendar.isPending}
              onClick={() => createCalendar.mutate({
                year: Number(calendarYear), name: calendarName,
              }, {
                onError: fail,
                onSuccess: () => success("Draft holiday calendar created."),
              })}
            >
              Create draft calendar
            </Button>
            <Select
              label="Draft calendar"
              data={(calendars.data?.results ?? []).map((calendar) => ({
                value: String(calendar.id),
                label: `${calendar.year} · ${calendar.name} (${calendar.status})`,
              }))}
              value={selectedCalendar}
              onChange={setSelectedCalendar}
            />
            {selectedCalendarValue?.status === "draft" && (
              <>
                <Group grow>
                  <TextInput
                    label="Holiday date"
                    type="date"
                    value={holidayDate}
                    onChange={(event) => setHolidayDate(event.currentTarget.value)}
                  />
                  <TextInput
                    label="Holiday name"
                    value={holidayName}
                    onChange={(event) => setHolidayName(event.currentTarget.value)}
                  />
                  <Select
                    label="Holiday kind"
                    data={[
                      { value: "closed", label: "Closed" },
                      { value: "restricted", label: "Restricted" },
                    ]}
                    value={holidayKind}
                    onChange={setHolidayKind}
                  />
                </Group>
                <Button
                  disabled={!holidayDate || !holidayName.trim() || !holidayKind}
                  loading={addHoliday.isPending}
                  onClick={() => addHoliday.mutate({
                    date: holidayDate,
                    name: holidayName,
                    kind: holidayKind === "restricted" ? "restricted" : "closed",
                  }, {
                    onError: fail,
                    onSuccess: () => success("Holiday added to the draft."),
                  })}
                >
                  Add holiday
                </Button>
                <Button
                  color="green"
                  loading={publishCalendar.isPending}
                  onClick={() => publishCalendar.mutate(
                    Number(selectedCalendar),
                    {
                      onError: fail,
                      onSuccess: () => success("Holiday calendar published."),
                    },
                  )}
                >
                  Publish calendar
                </Button>
              </>
            )}
          </Stack>
        </Card>
        <Card withBorder>
          <Stack>
            <Title order={4}>Academic vacation periods</Title>
            <Text size="sm">
              Vacation Leave requests are limited to these configured periods.
            </Text>
            <Group grow>
              <TextInput
                label="Academic year"
                value={vacationAcademicYear}
                onChange={(event) => setVacationAcademicYear(event.currentTarget.value)}
              />
              <TextInput
                label="Period label"
                value={vacationLabel}
                onChange={(event) => setVacationLabel(event.currentTarget.value)}
              />
            </Group>
            <Group grow>
              <TextInput
                label="Start date"
                type="date"
                value={vacationStartsOn}
                onChange={(event) => setVacationStartsOn(event.currentTarget.value)}
              />
              <TextInput
                label="End date"
                type="date"
                value={vacationEndsOn}
                onChange={(event) => setVacationEndsOn(event.currentTarget.value)}
              />
            </Group>
            <Button
              disabled={!vacationAcademicYear.trim() || !vacationLabel.trim()
                || !vacationStartsOn || !vacationEndsOn
                || vacationEndsOn < vacationStartsOn}
              loading={createVacation.isPending}
              onClick={() => createVacation.mutate({
                academic_year: vacationAcademicYear,
                label: vacationLabel,
                starts_on: vacationStartsOn,
                ends_on: vacationEndsOn,
                source: "Institute Academic Calendar",
              }, {
                onError: fail,
                onSuccess: () => success("Vacation period configured."),
              })}
            >
              Add vacation period
            </Button>
          </Stack>
        </Card>
        </>
      )}
      {canManageEmployee && (
        <>
          <Card withBorder>
            <Stack>
              <Title order={4}>Organizational units</Title>
              <Group grow>
                <TextInput
                  label="Unit code"
                  value={unitCode}
                  onChange={(event) => setUnitCode(event.currentTarget.value)}
                />
                <TextInput
                  label="Unit name"
                  value={unitName}
                  onChange={(event) => setUnitName(event.currentTarget.value)}
                />
                <NumberInput
                  label="Unit head user ID"
                  min={1}
                  value={unitHead}
                  onChange={setUnitHead}
                />
              </Group>
              <Button
                disabled={!unitCode.trim() || !unitName.trim()
                  || !Number.isInteger(Number(unitHead)) || Number(unitHead) <= 0}
                loading={createUnit.isPending}
                onClick={() => createUnit.mutate({
                  code: unitCode.trim().toLowerCase().replaceAll(" ", "-"),
                  name: unitName.trim(),
                  unit_head_user_id: Number(unitHead),
                }, {
                  onError: fail,
                  onSuccess: () => success("Organizational unit created."),
                })}
              >
                Create unit
              </Button>
              {(units.data?.results ?? []).map((unit) => (
                <Text key={unit.id} size="sm">
                  {unit.name} · head user {unit.unit_head_user_id}
                </Text>
              ))}
            </Stack>
          </Card>
          <Card withBorder>
            <Stack>
              <Title order={4}>Employee leave profile</Title>
              <NumberInput
                label="Employee user ID"
                min={1}
                value={profileUser}
                onChange={setProfileUser}
              />
              <Select
                label="Employee kind"
                data={["faculty", "staff"]}
                value={profileKind}
                onChange={setProfileKind}
              />
              <Select
                label="Organizational unit"
                data={(units.data?.results ?? []).map((unit) => ({
                  value: String(unit.id), label: unit.name,
                }))}
                value={profileUnit}
                onChange={setProfileUnit}
              />
              <TextInput
                label="Designation"
                value={designation}
                onChange={(event) => setDesignation(event.currentTarget.value)}
              />
              <Checkbox
                label="Requires substitute consent"
                checked={requiresSubstitute}
                onChange={(event) => setRequiresSubstitute(event.currentTarget.checked)}
              />
              <Checkbox
                label="Director"
                checked={isDirector}
                onChange={(event) => setIsDirector(event.currentTarget.checked)}
              />
              <Button
                disabled={!Number.isInteger(Number(profileUser))
                  || Number(profileUser) <= 0 || !profileUnit || !profileKind}
                loading={maintainProfile.isPending}
                onClick={() => maintainProfile.mutate({
                  user_id: Number(profileUser),
                  employee_kind: profileKind === "faculty" ? "faculty" : "staff",
                  unit_id: Number(profileUnit),
                  designation,
                  requires_substitute: requiresSubstitute,
                  is_director: isDirector,
                  is_active: true,
                }, {
                  onError: fail,
                  onSuccess: () => success("Employee leave profile saved."),
                })}
              >
                Save employee profile
              </Button>
            </Stack>
          </Card>
        </>
      )}
      {can("employee_leave.request.process") && (
        <Card withBorder>
          <Stack>
            <Title order={4}>Maintain an approved leave record</Title>
            <Text size="sm">
              This capability only corrects record details. It cannot change
              dates, category, workflow, or sanction state.
            </Text>
            <NumberInput
              label="Leave request ID"
              min={1}
              value={recordId}
              onChange={setRecordId}
            />
            <TextInput
              label="Corrected purpose (optional)"
              value={correctedPurpose}
              onChange={(event) => setCorrectedPurpose(event.currentTarget.value)}
            />
            <TextInput
              label="Corrected offline reference (optional)"
              value={correctedReference}
              onChange={(event) => setCorrectedReference(event.currentTarget.value)}
            />
            <Textarea
              label="Reason for correction"
              value={maintenanceReason}
              onChange={(event) => setMaintenanceReason(event.currentTarget.value)}
            />
            <Button
              disabled={!Number.isInteger(Number(recordId)) || Number(recordId) <= 0
                || !maintenanceReason.trim()
                || (!correctedPurpose.trim() && !correctedReference.trim())}
              loading={maintainRecord.isPending}
              onClick={() => maintainRecord.mutate({
                id: Number(recordId),
                reason: maintenanceReason,
                ...(correctedPurpose.trim() ? { purpose: correctedPurpose } : {}),
                ...(correctedReference.trim()
                  ? { offline_reference: correctedReference } : {}),
              }, {
                onError: fail,
                onSuccess: (updated) => success(`Record ${updated.id} corrected and audited.`),
              })}
            >
              Save audited correction
            </Button>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}
