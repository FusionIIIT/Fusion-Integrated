import {
  Alert, Badge, Button, Card, Container, Group, List, NumberInput, Select, SimpleGrid, Stack,
  Table, Tabs, Text, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { useState } from "react";
import { FaClipboardList } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAdjust, useEmployeeRecord, useReadiness, useRecordOffline, useYearEnd,
} from "../api/hooks";
import type { Category, LeaveRequest } from "../api/types";
import { LeaveDate, LeaveStatus, SubstitutePicker, period } from "../components/fields";
import { RequestDrawer } from "../components/RequestDrawer";

const CATEGORIES: Category[] = ["CL", "RH", "SCL", "EL", "COL", "VL"];

/** EL-UC-016/017: an employee's record, offline sanctions and corrections; none is a sanction. */
export default function RecordsPage() {
  const { can } = useAuth();
  const [userId, setUserId] = useState<number | null>(null);
  const [year, setYear] = useState(dayjs().year());
  const record = useEmployeeRecord(userId, year);
  const readiness = useReadiness();
  const yearEnd = useYearEnd();
  const [dialog, setDialog] = useState<null | "offline" | "adjust">(null);
  const [open, setOpen] = useState<number | null>(null);

  return (
    <Container size="xl">
      <PageHeader title="Leave Records" subtitle="Any employee's leave account and history" />
      {readiness.data && !readiness.data.ready && (
        <Alert color="red" mb="md" title="Leave is not ready">
          <List size="sm">{readiness.data.unmet.map((u) => <List.Item key={u}>{u}</List.Item>)}</List>
        </Alert>)}
      <Tabs defaultValue="employee">
        <Tabs.List>
          <Tabs.Tab value="employee">Employee record</Tabs.Tab>
          <Tabs.Tab value="year-end">Year-end runs</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="employee" pt="md">
          <Group align="flex-end" mb="md">
            <SubstitutePicker label="Employee" value={userId} onChange={setUserId} />
            <NumberInput label="Year" w={100} value={year} onChange={(v) => setYear(Number(v) || year)} />
            {can("leave.record.import") && <Button variant="light" disabled={userId == null}
              onClick={() => setDialog("offline")}>Record offline sanction</Button>}
            {can("leave.record.update") && <Button variant="light" disabled={userId == null}
              onClick={() => setDialog("adjust")}>Correct a balance</Button>}
          </Group>
          {record.error && <ErrorState error={record.error} />}
          {userId == null && <Text c="dimmed">Choose an employee to see their record.</Text>}
          {record.data && (
            <Stack>
              <Title order={4}>{record.data.person?.display_name ?? `User ${userId}`}
                {" "}<Text span c="dimmed" size="sm">{record.data.person?.department}</Text></Title>
              <SimpleGrid cols={{ base: 3, md: 6 }}>
                {record.data.balances.filter((b) => b.applicable).map((b) => (
                  <Card key={b.category} withBorder padding="sm">
                    <Text size="xs" c="dimmed">{b.category}</Text>
                    <Text fw={700}>{Number(b.balance)}</Text>
                  </Card>))}
              </SimpleGrid>
              <Card padding="md">
                <DataTable<LeaveRequest> rows={record.data.requests} rowKey={(r) => r.id}
                  columns={[
                    { key: "id", header: "#", render: (r) => <Button size="compact-sm" variant="subtle"
                      onClick={() => setOpen(r.id)}>#{r.id}</Button> },
                    { key: "category", header: "Leave", render: (r) => `${r.category} · ${r.kind}` },
                    { key: "period", header: "Period", render: (r) => period(r) },
                    { key: "status", header: "Status", render: (r) => (
                      <Group gap={4}><LeaveStatus status={r.status} label={r.status_label} />
                        {r.source === "offline" && <Badge size="xs" color="gray">offline</Badge>}</Group>) },
                  ]}
                  empty={{ icon: FaClipboardList, title: `No requests in ${year}` }} />
              </Card>
              <Card padding="md">
                <Table>
                  <Table.Thead><Table.Tr><Table.Th>Date</Table.Th><Table.Th>Leave</Table.Th>
                    <Table.Th>Entry</Table.Th><Table.Th>Days</Table.Th><Table.Th>Note</Table.Th></Table.Tr></Table.Thead>
                  <Table.Tbody>{record.data.ledger.map((e) => (
                    <Table.Tr key={e.id}><Table.Td>{dayjs(e.created_at).format("DD MMM YYYY")}</Table.Td>
                      <Table.Td>{e.category}</Table.Td><Table.Td>{e.entry_label}</Table.Td>
                      <Table.Td>{Number(e.delta)}</Table.Td><Table.Td>{e.note}</Table.Td></Table.Tr>))}
                  </Table.Tbody>
                </Table>
              </Card>
            </Stack>)}
        </Tabs.Panel>
        <Tabs.Panel value="year-end" pt="md">
          {yearEnd.error && <ErrorState error={yearEnd.error} />}
          <Card padding="md">
            {!yearEnd.data?.length && <Text c="dimmed">Year-end has not run yet.</Text>}
            {(yearEnd.data ?? []).map((r) => (
              <Stack key={r.year} gap={4} mb="md">
                <Group><Text fw={700}>{r.year}</Text><LeaveStatus status={r.status} />
                  <Text size="sm" c="dimmed">{r.accounts_processed} account(s), {r.entries_written} entries</Text></Group>
                {r.exceptions.map((e) => <Text key={e.user_id} size="sm" c="orange">
                  User {e.user_id}: {e.reason}</Text>)}
              </Stack>))}
          </Card>
        </Tabs.Panel>
      </Tabs>
      {userId != null && <RecordDialogs dialog={dialog} userId={userId} year={year}
        onClose={() => setDialog(null)} />}
      <RequestDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}

function RecordDialogs({ dialog, userId, year, onClose }: {
  dialog: null | "offline" | "adjust"; userId: number; year: number; onClose: () => void;
}) {
  const offline = useRecordOffline();
  const adjust = useAdjust();
  const [category, setCategory] = useState<Category>("CL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [reference, setReference] = useState("");
  const [reason, setReason] = useState("illness");
  const [note, setNote] = useState("");
  const [delta, setDelta] = useState<number | string>("");
  const done = (title: string) => ({ onSuccess: () => {
    notifications.show({ color: "green", title, message: `User ${userId}` }); onClose(); } });

  if (dialog === "offline") {
    return (
      <FormModal opened onClose={onClose} title="Record offline-sanctioned leave"
        subtitle="Synchronises the record; it is not a new approval" submitting={offline.isPending}
        error={offline.error} disabled={!start || !end || !reference.trim()}
        disabledReason="Dates and the sanction reference are required."
        onSubmit={() => offline.mutate({ user_id: userId, category, start_date: start, end_date: end,
          sanction_reference: reference, reason, reason_detail: note, purpose: note }, done("Recorded"))}>
        <Stack>
          <Select label="Category" data={CATEGORIES} value={category}
            onChange={(v) => setCategory((v ?? "CL") as Category)} />
          <Group grow><LeaveDate label="From" value={start} onChange={setStart} required />
            <LeaveDate label="To" value={end} onChange={setEnd} minDate={start} required /></Group>
          <TextInput label="Sanction order / reference" required value={reference}
            onChange={(e) => setReference(e.currentTarget.value)} />
          <Select label="Why ELM was not used" value={reason} onChange={(v) => setReason(v ?? "other")}
            data={[{ value: "illness", label: "Illness" }, { value: "connectivity", label: "Connectivity" },
              { value: "server_unavailable", label: "Server unavailable" }, { value: "other", label: "Other" }]} />
          <TextInput label="Detail" value={note} onChange={(e) => setNote(e.currentTarget.value)} />
        </Stack>
      </FormModal>);
  }
  if (dialog === "adjust") {
    return (
      <FormModal opened onClose={onClose} title="Correct a balance"
        subtitle={`A new ledger entry for ${year}; nothing is edited`} submitting={adjust.isPending}
        error={adjust.error} disabled={delta === "" || !reference.trim() || !note.trim()}
        disabledReason="Days, a reference and a reason are required."
        onSubmit={() => adjust.mutate({ user_id: userId, year, category, delta: String(delta),
          reference, note }, done("Adjusted"))}>
        <Stack>
          <Select label="Category" data={CATEGORIES} value={category}
            onChange={(v) => setCategory((v ?? "CL") as Category)} />
          <NumberInput label="Days (negative to deduct)" step={0.5} decimalScale={1} value={delta}
            onChange={setDelta} />
          <TextInput label="Office reference" required value={reference}
            onChange={(e) => setReference(e.currentTarget.value)} />
          <TextInput label="Reason" required value={note} onChange={(e) => setNote(e.currentTarget.value)} />
        </Stack>
      </FormModal>);
  }
  return null;
}
