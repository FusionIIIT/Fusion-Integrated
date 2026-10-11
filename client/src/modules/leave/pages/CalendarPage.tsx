import { useState } from "react";
import { Button, Card, Container, Select, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCalendar, usePublishCalendar } from "../api/hooks";

export default function CalendarPage() {
  const { data } = useCalendar();
  const publish = usePublishCalendar();
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [kind, setKind] = useState<string | null>("rh");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [label, setLabel] = useState("");

  function save() {
    const existing = (data?.entries ?? []) as Array<{
      kind: string; start_on: string; end_on: string; label: string;
    }>;
    publish.mutate({
      year: Number(year),
      label: `Calendar ${year}`,
      entries: [...existing, { kind, start_on: start, end_on: end || start, label }],
    }, {
      onSuccess: () => notifications.show({ color: "green", message: "Calendar published" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="sm">
      <PageHeader title="Holiday / RH calendar" subtitle="Date and RH validations use the currently published calendar" />
      <Card padding="lg">
        <Stack>
          <Text size="sm" c="dimmed">Effective version {data?.version ?? "none"} ({data?.entries?.length ?? 0} entries)</Text>
          <TextInput label="Year" value={year} onChange={(e) => setYear(e.target.value)} />
          <Select label="Entry kind" value={kind} onChange={setKind}
            data={[{ value: "closed", label: "Closed holiday" },
                   { value: "rh", label: "Restricted holiday" },
                   { value: "vacation", label: "Vacation period" }]} />
          <TextInput type="date" label="Start" value={start} onChange={(e) => setStart(e.target.value)} />
          <TextInput type="date" label="End" value={end} onChange={(e) => setEnd(e.target.value)} />
          <TextInput label="Label" value={label} onChange={(e) => setLabel(e.target.value)} />
          <Button onClick={save} loading={publish.isPending}>Publish replacement including this entry</Button>
        </Stack>
      </Card>
    </Container>
  );
}
