import {
  ActionIcon, Badge, Button, Card, Container, Group, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaTrash } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCalendars, useCreateCalendar, usePublishCalendar } from "../api/hooks";
import type { CalendarEntry } from "../api/types";

const KINDS = [
  { value: "closed_holiday", label: "Closed holiday" },
  { value: "restricted_holiday", label: "Restricted holiday" },
  { value: "vacation", label: "Vacation period" },
];

export default function CalendarPage() {
  const { data, isPending, error } = useCalendars();
  const create = useCreateCalendar();
  const publish = usePublishCalendar();
  const [draft, setDraft] = useState<{ name: string; from: string;
    entries: CalendarEntry[] } | null>(null);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const setEntry = (i: number, e: Partial<CalendarEntry>) => draft && setDraft({
    ...draft, entries: draft.entries.map((x, j) => (j === i ? { ...x, ...e } : x)) });

  return (
    <Container size="xl">
      <PageHeader title="Holiday Calendar"
        subtitle="Closed holidays, Restricted Holidays and vacation periods"
        action={<Button onClick={() => setDraft({ name: "", from: "", entries: [] })}>
          New version</Button>} />
      <Card withBorder padding="md">
        <DataTable rows={data?.results ?? []} loading={isPending} rowKey={(r) => r.id}
          empty={{ title: "No calendar published",
            description: "RH and VL requests are refused until one is published." }}
          columns={[
            { key: "name", header: "Version", render: (r) => <Text size="sm">#{r.id} {r.name}</Text> },
            { key: "from", header: "Effective from", render: (r) => r.effective_from },
            { key: "n", header: "Entries", render: (r) => r.entries.length },
            { key: "status", header: "Status",
              render: (r) => <Badge color={r.status === "published" ? "green" : "gray"}
                variant="light">{r.status}</Badge> },
            { key: "act", header: "", align: "right",
              render: (r) => r.status === "draft" && (
                <Button size="xs" onClick={() => publish.mutate(r.id, {
                  onError: (e) => notifications.show({ color: "red", title: "Not published",
                    message: errorMessage(e) }) })}>Publish</Button>) },
          ]} />
      </Card>
      {draft && (
        <FormModal opened title="New calendar version" onClose={() => setDraft(null)}
          size="xl" submitting={create.isPending} error={create.error}
          disabled={!draft.name || !draft.from} submitLabel="Save draft"
          onSubmit={() => create.mutate({ name: draft.name, effective_from: draft.from,
            entries: draft.entries }, { onSuccess: () => setDraft(null) })}>
          <Stack>
            <Group grow>
              <TextInput label="Name" value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.currentTarget.value })} />
              <TextInput type="date" label="Effective from" value={draft.from}
                onChange={(e) => setDraft({ ...draft, from: e.currentTarget.value })} />
            </Group>
            {draft.entries.map((e, i) => (
              <Group key={i} align="flex-end" wrap="nowrap">
                <Select data={KINDS} value={e.kind} allowDeselect={false} w={170}
                  onChange={(k) => setEntry(i, { kind: k as CalendarEntry["kind"] })} />
                <TextInput placeholder="Name" value={e.name} style={{ flex: 1 }}
                  onChange={(x) => setEntry(i, { name: x.currentTarget.value })} />
                <TextInput type="date" value={e.start_date}
                  onChange={(x) => setEntry(i, { start_date: x.currentTarget.value })} />
                <TextInput type="date" value={e.end_date}
                  onChange={(x) => setEntry(i, { end_date: x.currentTarget.value })} />
                <ActionIcon variant="subtle" color="red" aria-label="Remove"
                  onClick={() => setDraft({ ...draft,
                    entries: draft.entries.filter((_, j) => j !== i) })}>
                  <FaTrash size={12} /></ActionIcon>
              </Group>
            ))}
            <Button variant="light" onClick={() => setDraft({ ...draft, entries: [
              ...draft.entries, { kind: "closed_holiday", name: "", start_date: "",
                end_date: "" }] })}>Add entry</Button>
          </Stack>
        </FormModal>
      )}
    </Container>
  );
}
