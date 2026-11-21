import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAdminWrite, useCalendars } from "../api/hooks";
import type { Holiday } from "../api/types";
import { AdminForm } from "../components/AdminForm";

/** One holiday per line: `2027-01-26, Republic Day, closed`. */
export function parseHolidays(text: string): Holiday[] {
  return text.split("\n").map((l) => l.trim()).filter(Boolean).map((line) => {
    const [date, name, kind] = line.split(",").map((p) => p.trim());
    return { date: date ?? "", name: name ?? "",
      kind: kind === "restricted" ? "restricted" : "closed" };
  });
}

/** EL-UC-015: a revision is a new draft; publishing it replaces the current one. */
export default function CalendarPage() {
  const calendars = useCalendars();
  const write = useAdminWrite();
  const [year, setYear] = useState(String(new Date().getFullYear() + 1));
  const [lines, setLines] = useState("");
  const notify = { onError: (e: unknown) => notifications.show({ color: "red",
    title: "Not saved", message: errorMessage(e) }) };

  if (calendars.error) {
    return <Container size="xl"><ErrorState error={calendars.error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Holiday Calendar"
        subtitle="Leave dates are checked against the published calendar only" />
      <Card withBorder mb="md">
        <Text fw={600} mb="xs">New draft calendar</Text>
        <TextInput label="Year" w={120} value={year}
          onChange={(e) => setYear(e.currentTarget.value)} />
        <Textarea mt="sm" autosize minRows={4} label="Holidays"
          description="One per line: date, name, closed | restricted"
          value={lines} onChange={(e) => setLines(e.currentTarget.value)} />
        <Group justify="flex-end" mt="sm">
          <Button disabled={!lines.trim()} loading={write.isPending}
            onClick={() => write.mutate({ method: "post", path: "/leave/calendars", body: {
              year: Number(year), title: `Holidays ${year}`, holidays: parseHolidays(lines) } },
            { ...notify, onSuccess: () => setLines("") })}>
            Save draft
          </Button>
        </Group>
      </Card>

      {!calendars.isPending && !calendars.data?.length && (
        <Text c="dimmed" ta="center" py="lg">No calendars yet.</Text>
      )}
      <Stack>
        {(calendars.data ?? []).map((c) => (
          <Card key={c.id} withBorder>
            <Group justify="space-between">
              <Group><Text fw={600}>{c.title}</Text>
                <Badge color={c.status === "published" ? "green" : "gray"}>{c.status}</Badge>
              </Group>
              {c.status === "draft" && (
                <Button size="xs" onClick={() => write.mutate(
                  { method: "post", path: `/leave/calendars/${c.id}/publish` }, notify)}>
                  Publish
                </Button>)}
            </Group>
            <Text size="sm" c="dimmed" mt={4}>
              {c.holidays.map((h) => `${h.date} ${h.name}${h.kind === "restricted" ? " (RH)" : ""}`)
                .join(" · ") || "No holidays listed"}
            </Text>
          </Card>
        ))}
      </Stack>

      <AdminForm title="Vacation period (from the Academic Calendar)" path="/leave/vacations"
        fields={[{ name: "name", label: "Name" },
          { name: "start_date", label: "From", type: "date" },
          { name: "end_date", label: "To", type: "date" }]} />
    </Container>
  );
}
