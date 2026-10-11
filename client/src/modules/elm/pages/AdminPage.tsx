import { useState } from "react";
import {
  Button, Card, Container, Group, Modal, Select, Stack, TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCog } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { useAddHoliday, useHolidays } from "../api/hooks";
import type { Holiday } from "../api/types";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function AdminPage() {
  const { data, isPending, error } = useHolidays();
  const add = useAddHoliday();
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState<Date | null>(null);
  const [kind, setKind] = useState<string | null>("holiday");
  const [label, setLabel] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function submit() {
    if (!date || !kind) return;
    add.mutate(
      {
        date: date.toISOString().slice(0, 10), kind, label,
        is_published: true,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Holiday added",
                               message: "" });
          setOpen(false);
        },
        onError: (e) => notifications.show(
          { color: "red", title: "Could not add holiday", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Setup"
        subtitle="Holiday and restricted-holiday calendar"
        action={<Button onClick={() => setOpen(true)}>Add holiday</Button>}
      />

      <Card padding="lg">
        <DataTable<Holiday>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "date", header: "Date", render: (r) => r.date },
            { key: "kind", header: "Kind", render: (r) => r.kind },
            { key: "label", header: "Label", render: (r) => r.label || "—" },
          ]}
          empty={{
            icon: FaCog,
            title: "No holidays published",
            description: "Add the institute holiday calendar here.",
          }}
        />
      </Card>

      <Modal opened={open} onClose={() => setOpen(false)} title="Add holiday">
        <Stack gap="sm">
          <DateInput label="Date" value={date} onChange={setDate} />
          <Select label="Kind" value={kind} onChange={setKind}
                  data={[{ value: "holiday", label: "Closed holiday" },
                         { value: "restricted", label: "Restricted holiday" }]} />
          <TextInput label="Label" value={label}
                     onChange={(e) => setLabel(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button onClick={submit} loading={add.isPending}>Add</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
