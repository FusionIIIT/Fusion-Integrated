import {
  ActionIcon, Alert, Badge, Button, Card, Container, Group, NumberInput, Select, SimpleGrid,
  Stack, Table, Text, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { FaTrash } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAddVacation, useCalendars, usePublishCalendar, useRemoveVacation, useSaveCalendar,
  useStartCalendar, useVacations,
} from "../api/hooks";
import type { Holiday } from "../api/types";
import { LeaveDate } from "../components/fields";

/** EL-UC-015: drafts never govern; publishing replaces the effective calendar (BR-EL-031). */
export default function CalendarPage() {
  const { can } = useAuth();
  const [year, setYear] = useState(dayjs().year());
  const calendars = useCalendars(year);
  const start = useStartCalendar();
  const save = useSaveCalendar();
  const publish = usePublishCalendar();
  const draft = calendars.data?.find((c) => c.status === "draft");
  const published = calendars.data?.find((c) => c.status === "published");
  const [rows, setRows] = useState<Holiday[]>([]);

  useEffect(() => { setRows(draft?.holidays ?? []); }, [draft?.id, draft?.holidays]);

  const toast = (title: string) => ({
    onSuccess: () => notifications.show({ color: "green", title, message: `${year}` }),
    onError: (e: unknown) => notifications.show({ color: "red", title: "Not saved",
      message: errorMessage(e) }),
  });

  return (
    <Container size="xl">
      <PageHeader title="Holiday Calendar"
        subtitle="Closed holidays and Restricted Holidays that leave validation uses"
        action={<NumberInput value={year} onChange={(v) => setYear(Number(v) || year)}
          min={2000} max={2100} w={110} />} />
      {calendars.error && <ErrorState error={calendars.error} />}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <Card padding="lg" withBorder>
          <Group justify="space-between" mb="sm">
            <Title order={4}>In effect</Title>
            {published ? <Badge color="green">v{published.version}</Badge>
              : <Badge color="red">none published</Badge>}
          </Group>
          {!published && <Alert color="yellow">Nobody can apply for leave in {year} until a
            calendar is published.</Alert>}
          <HolidayTable rows={published?.holidays ?? []} />
        </Card>
        <Card padding="lg" withBorder>
          <Group justify="space-between" mb="sm">
            <Title order={4}>Draft</Title>
            {!draft && <Button size="xs" loading={start.isPending}
              onClick={() => start.mutate(year, toast("Draft started"))}>
              {published ? "Start a revision" : "Start the calendar"}</Button>}
          </Group>
          {draft ? (
            <Stack>
              <HolidayTable rows={rows} onChange={setRows} />
              <Group justify="flex-end">
                <Button variant="default" size="xs" loading={save.isPending}
                  onClick={() => save.mutate({ id: draft.id, holidays: rows }, toast("Draft saved"))}>
                  Save draft</Button>
                {can("leave.calendar.publish") && <Button size="xs" loading={publish.isPending}
                  onClick={() => save.mutate({ id: draft.id, holidays: rows }, {
                    onSuccess: () => publish.mutate(draft.id, toast("Published")),
                    onError: toast("").onError })}>Publish</Button>}
              </Group>
            </Stack>
          ) : <Text c="dimmed" size="sm">No draft. A revision starts as a copy of what is in effect.</Text>}
        </Card>
      </SimpleGrid>
      <Vacations />
    </Container>
  );
}

function HolidayTable({ rows, onChange }: { rows: Holiday[]; onChange?: (r: Holiday[]) => void }) {
  const [date, setDate] = useState("");
  const [name, setName] = useState("");
  const [kind, setKind] = useState<Holiday["kind"]>("closed");
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  return (
    <Stack gap="xs">
      <Table striped>
        <Table.Tbody>
          {sorted.map((h) => (
            <Table.Tr key={h.date}>
              <Table.Td>{dayjs(h.date).format("ddd DD MMM")}</Table.Td>
              <Table.Td>{h.name}</Table.Td>
              <Table.Td><Badge size="xs" color={h.kind === "closed" ? "blue" : "grape"}>
                {h.kind}</Badge></Table.Td>
              {onChange && <Table.Td><ActionIcon variant="subtle" color="red" aria-label="Remove"
                onClick={() => onChange(rows.filter((r) => r.date !== h.date))}>
                <FaTrash size={11} /></ActionIcon></Table.Td>}
            </Table.Tr>))}
        </Table.Tbody>
      </Table>
      {!rows.length && <Text size="sm" c="dimmed">No holidays.</Text>}
      {onChange && (
        <Group align="flex-end" gap="xs">
          <LeaveDate label="Date" value={date} onChange={setDate} />
          <TextInput label="Name" value={name} onChange={(e) => setName(e.currentTarget.value)} />
          <Select label="Kind" w={130} value={kind} onChange={(v) => setKind((v ?? "closed") as Holiday["kind"])}
            data={[{ value: "closed", label: "Closed" }, { value: "restricted", label: "Restricted" }]} />
          <Button size="sm" variant="light" disabled={!date || !name.trim()}
            onClick={() => { onChange([...rows.filter((r) => r.date !== date), { date, name, kind }]);
              setDate(""); setName(""); }}>Add</Button>
        </Group>)}
    </Stack>
  );
}

function Vacations() {
  const { data, error } = useVacations();
  const add = useAddVacation();
  const remove = useRemoveVacation();
  const [label, setLabel] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [ref, setRef] = useState("");
  return (
    <Card padding="lg" withBorder mt="lg">
      <Title order={4}>Vacation periods</Title>
      <Text size="sm" c="dimmed" mb="sm">As published in the institute Academic Calendar;
        Vacation Leave can only be taken inside one.</Text>
      {error && <ErrorState error={error} />}
      <Table>
        <Table.Tbody>
          {(data ?? []).map((v) => (
            <Table.Tr key={v.id}>
              <Table.Td>{v.label}</Table.Td>
              <Table.Td>{dayjs(v.start_date).format("DD MMM YYYY")} – {dayjs(v.end_date).format("DD MMM YYYY")}</Table.Td>
              <Table.Td>{v.source_reference}</Table.Td>
              <Table.Td><ActionIcon variant="subtle" color="red" aria-label="Remove"
                onClick={() => remove.mutate(v.id)}><FaTrash size={11} /></ActionIcon></Table.Td>
            </Table.Tr>))}
        </Table.Tbody>
      </Table>
      {!data?.length && <Text size="sm" c="dimmed">None recorded.</Text>}
      <Group align="flex-end" gap="xs" mt="sm">
        <TextInput label="Name" value={label} onChange={(e) => setLabel(e.currentTarget.value)} />
        <LeaveDate label="From" value={from} onChange={setFrom} />
        <LeaveDate label="To" value={to} onChange={setTo} minDate={from} />
        <TextInput label="Academic Calendar reference" value={ref}
          onChange={(e) => setRef(e.currentTarget.value)} />
        <Button variant="light" loading={add.isPending} disabled={!label.trim() || !from || !to}
          onClick={() => add.mutate({ label, start_date: from, end_date: to, source_reference: ref }, {
            onSuccess: () => { setLabel(""); setFrom(""); setTo(""); setRef(""); },
            onError: (e) => notifications.show({ color: "red", title: "Not added",
              message: errorMessage(e) }) })}>Add</Button>
      </Group>
    </Card>
  );
}
