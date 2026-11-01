import { useState } from "react";
import {
  Alert, Button, Checkbox, Container, Group, NumberInput, Select, Stack,
  Table, Text, TextInput, Title,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { formatLocalDate } from "../utils/dates";
import {
  useAdjustBalance, useCreateHoliday, useCreatePolicy, useLeaveCalendar,
  useLeavePolicies, useProcessYearEnd, usePublishHoliday, useRecordOfflineLeave,
} from "../api/hooks";

const types = ["CL", "RH", "SCL", "EL", "VL", "COL"];

export default function AdminPage() {
  const policies = useLeavePolicies();
  const calendar = useLeaveCalendar();
  const createPolicy = useCreatePolicy();
  const createHoliday = useCreateHoliday();
  const publishHoliday = usePublishHoliday();
  const adjust = useAdjustBalance();
  const offline = useRecordOfflineLeave();
  const yearEnd = useProcessYearEnd();
  const [type, setType] = useState<string | null>("CL");
  const [year, setYear] = useState<number | "">(new Date().getFullYear());
  const [entitlement, setEntitlement] = useState<number | "">(12);
  const [carry, setCarry] = useState<number | "">(0);
  const [maxDays, setMaxDays] = useState<number | "">("");
  const [yearEndTreatment, setYearEndTreatment] = useState<string | null>("lapse");
  const [conversionRatio, setConversionRatio] = useState<number | "">(1);
  const [substitute, setSubstitute] = useState(false);
  const [higher, setHigher] = useState(false);
  const [faculty, setFaculty] = useState(false);
  const [finalRole, setFinalRole] = useState("sanctioning_authority");
  const [establishmentRequired, setEstablishmentRequired] = useState(false);
  const [holidayName, setHolidayName] = useState("");
  const [holidayDate, setHolidayDate] = useState<Date | null>(null);
  const [restricted, setRestricted] = useState(false);
  const [userId, setUserId] = useState("");
  const [policyId, setPolicyId] = useState("");
  const [days, setDays] = useState<number | "">(0);
  const [entryType, setEntryType] = useState<string | null>("opening");
  const [offlineUser, setOfflineUser] = useState("");
  const [offlineType, setOfflineType] = useState<string | null>("CL");
  const [offlineStart, setOfflineStart] = useState<Date | null>(null);
  const [offlineEnd, setOfflineEnd] = useState<Date | null>(null);
  const [offlineReason, setOfflineReason] = useState("");
  const policyRows = policies.data?.pages.flatMap((page) => page.results) ?? [];
  const holidayRows = calendar.data?.pages.flatMap((page) => page.results) ?? [];

  if (policies.error || calendar.error) return <Container size="xl"><ErrorState error={policies.error ?? calendar.error} /></Container>;
  function notifyError(error: unknown) {
    notifications.show({ color: "red", message: errorMessage(error) });
  }

  function runYearEnd() {
    const fromYear = (typeof year === "number" ? year : new Date().getFullYear()) - 1;
    if (!window.confirm(`Process leave accounts for ${fromYear}? This operation can run only once.`)) {
      return;
    }
    yearEnd.mutate(fromYear, {
      onSuccess: (run) => notifications.show({
        color: "green", title: `Leave accounts processed: ${run.from_year}`,
        message: `${run.balances_processed} accounts · ${run.carried_forward} carried · ${run.converted_to_el} converted to EL · ${run.lapsed} lapsed`,
      }),
      onError: notifyError,
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Administration" subtitle="Current policy, holiday calendar and account maintenance" />
      <Stack gap="xl">
        <section>
          <Title order={4} mb="sm">Leave policies</Title>
          <Group align="end" grow wrap="wrap">
            <Select label="Category" data={types} value={type} onChange={(value) => {
              setType(value);
              if (value !== "VL" && yearEndTreatment === "convert_to_el") {
                setYearEndTreatment("lapse");
              }
            }} />
            <NumberInput label="Leave year" value={year} min={2000} max={2200}
              onChange={(value) => setYear(typeof value === "number" ? value : "")} />
            <NumberInput label="Annual entitlement" min={0} decimalScale={2} value={entitlement}
              onChange={(value) => setEntitlement(typeof value === "number" ? value : "")} />
            <NumberInput label="Carry-forward limit" min={0} decimalScale={2} value={carry}
              onChange={(value) => setCarry(typeof value === "number" ? value : "")} />
            <NumberInput label="Max continuous days" min={1} value={maxDays}
              onChange={(value) => setMaxDays(typeof value === "number" ? value : "")} />
            <Select label="Year-end treatment" data={[
              { value: "lapse", label: "Lapse" },
              { value: "carry_forward", label: "Carry forward" },
              ...(type === "VL" ? [{ value: "convert_to_el", label: "Convert to EL" }] : []),
            ]} value={yearEndTreatment} onChange={setYearEndTreatment} />
            {yearEndTreatment === "convert_to_el" && <NumberInput label="Conversion ratio" min={0}
              decimalScale={3} value={conversionRatio}
              onChange={(value) => setConversionRatio(typeof value === "number" ? value : "")} />}
          </Group>
          <Group mt="sm" mb="sm">
            <Checkbox label="Requires substitute" checked={substitute} onChange={(e) => setSubstitute(e.currentTarget.checked)} />
            <Checkbox label="Higher sanction" checked={higher} onChange={(e) => setHigher(e.currentTarget.checked)} />
            <Checkbox label="Faculty only" checked={faculty} onChange={(e) => setFaculty(e.currentTarget.checked)} />
            <Checkbox label="Establishment verification" checked={establishmentRequired}
              onChange={(e) => setEstablishmentRequired(e.currentTarget.checked)} />
            <TextInput label="Final authority role" value={finalRole}
              onChange={(e) => setFinalRole(e.currentTarget.value)} />
            <Button loading={createPolicy.isPending} disabled={!type || !year}
              onClick={() => createPolicy.mutate({
                leave_type: type, leave_year: year, annual_entitlement: entitlement,
                carry_forward_limit: carry, max_continuous_days: maxDays || null,
                year_end_treatment: yearEndTreatment, conversion_ratio: conversionRatio,
                requires_substitute: substitute, requires_higher_sanction: higher,
                faculty_only: faculty,
                hierarchy: { final_role: finalRole, establishment_required: establishmentRequired },
              }, { onError: notifyError })}>Add policy</Button>
          </Group>
          <Table.ScrollContainer minWidth={660}><Table striped><Table.Thead><Table.Tr>
            <Table.Th>Year</Table.Th><Table.Th>Type</Table.Th><Table.Th>Entitlement</Table.Th>
            <Table.Th>Carry limit</Table.Th><Table.Th>Workflow</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{policyRows.map((row) => <Table.Tr key={row.id}>
              <Table.Td>{row.leave_year}</Table.Td><Table.Td>{row.leave_type}</Table.Td>
              <Table.Td>{row.annual_entitlement}</Table.Td><Table.Td>{row.carry_forward_limit}</Table.Td>
              <Table.Td>{row.requires_substitute ? "Substitute · " : ""}{row.requires_higher_sanction ? "Higher sanction" : "Unit Head"}</Table.Td>
            </Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>
          {policies.hasNextPage && <Button mt="xs" variant="default"
            loading={policies.isFetchingNextPage} onClick={() => policies.fetchNextPage()}>
            Load more policies
          </Button>}
        </section>

        <section>
          <Title order={4} mb="sm">Holiday and restricted-holiday calendar</Title>
          <Group align="end" grow wrap="wrap">
            <NumberInput label="Year" value={year} min={2000} max={2200}
              onChange={(value) => setYear(typeof value === "number" ? value : "")} />
            <DateInput label="Date" value={holidayDate} onChange={setHolidayDate} valueFormat="DD MMM YYYY" />
            <TextInput label="Name" value={holidayName} onChange={(e) => setHolidayName(e.currentTarget.value)} />
            <Checkbox label="Restricted holiday" checked={restricted} onChange={(e) => setRestricted(e.currentTarget.checked)} />
            <Button loading={createHoliday.isPending} disabled={!holidayDate || !holidayName.trim()}
              onClick={() => createHoliday.mutate({
                leave_year: year, day: holidayDate && formatLocalDate(holidayDate),
                name: holidayName, restricted,
              }, { onError: notifyError })}>Add calendar entry</Button>
          </Group>
          <Table mt="sm"><Table.Thead><Table.Tr><Table.Th>Date</Table.Th><Table.Th>Name</Table.Th>
            <Table.Th>Kind</Table.Th><Table.Th>Status</Table.Th><Table.Th /></Table.Tr></Table.Thead>
            <Table.Tbody>{holidayRows.map((row) => <Table.Tr key={row.id}>
              <Table.Td>{row.day}</Table.Td><Table.Td>{row.name}</Table.Td>
              <Table.Td>{row.restricted ? "Restricted" : "Holiday"}</Table.Td>
              <Table.Td>{row.published ? "Published" : "Draft"}</Table.Td>
              <Table.Td>{!row.published && <Button size="xs" variant="light"
                loading={publishHoliday.isPending} onClick={() => publishHoliday.mutate(row.id,
                  { onError: notifyError })}>Publish</Button>}</Table.Td>
            </Table.Tr>)}</Table.Tbody></Table>
          {calendar.hasNextPage && <Button mt="xs" variant="default"
            loading={calendar.isFetchingNextPage} onClick={() => calendar.fetchNextPage()}>
            Load more calendar entries
          </Button>}
        </section>

        <section>
          <Title order={4} mb="sm">Balance maintenance</Title>
          <Group align="end" grow wrap="wrap">
            <TextInput label="Employee ID" value={userId} onChange={(e) => setUserId(e.currentTarget.value)} />
            <Select label="Policy" data={policyRows.map((row) => ({
              value: String(row.id), label: `${row.leave_year} · ${row.leave_type}`,
            }))} value={policyId || null} onChange={(value) => setPolicyId(value ?? "")} />
            <Select label="Entry" data={[{ value: "opening", label: "Set opening balance" },
              { value: "credit", label: "Add credit" }]} value={entryType} onChange={setEntryType} />
            <NumberInput label="Days" min={0} decimalScale={2} value={days}
              onChange={(value) => setDays(typeof value === "number" ? value : "")} />
            <Button loading={adjust.isPending} disabled={!userId || !policyId || !entryType}
              onClick={() => adjust.mutate({ user_id: Number(userId), policy_id: Number(policyId),
                entry_type: entryType, days, description: "Administrator account maintenance" },
              { onError: notifyError })}>Post balance entry</Button>
          </Group>
          <Alert mt="sm" color="gray">Adjustments are recorded in the employee's leave ledger.</Alert>
        </section>

        <section>
          <Title order={4} mb="sm">Year-end account processing</Title>
          <Text size="sm" c="dimmed" mb="sm">
            Close the prior year, apply configured lapse/carry/conversion rules and post the new year's credits.
          </Text>
          <Button color="red" loading={yearEnd.isPending}
            onClick={runYearEnd}>Process previous leave year</Button>
        </section>

        <section>
          <Title order={4} mb="sm">Record sanctioned offline leave</Title>
          <Group align="end" grow wrap="wrap">
            <TextInput label="Employee ID" value={offlineUser}
              onChange={(e) => setOfflineUser(e.currentTarget.value)} />
            <Select label="Category" data={types} value={offlineType} onChange={setOfflineType} />
            <DateInput label="From" value={offlineStart} onChange={setOfflineStart} />
            <DateInput label="Through" value={offlineEnd} onChange={setOfflineEnd} />
            <TextInput label="Authorization reference / reason" value={offlineReason}
              onChange={(e) => setOfflineReason(e.currentTarget.value)} />
            <Button loading={offline.isPending}
              disabled={!offlineUser || !offlineType || !offlineStart || !offlineEnd || !offlineReason.trim()}
              onClick={() => offline.mutate({
                user_id: Number(offlineUser), leave_type: offlineType, leave_year: year,
                start_date: offlineStart && formatLocalDate(offlineStart),
                end_date: offlineEnd && formatLocalDate(offlineEnd), reason: offlineReason,
              }, { onSuccess: () => { setOfflineUser(""); setOfflineReason(""); },
                onError: notifyError })}>Record leave</Button>
          </Group>
        </section>
      </Stack>
    </Container>
  );
}