import { useState } from "react";
import {
  Badge, Button, Card, Checkbox, Container, Group, Select, Stack, Text,
  TextInput, Textarea, Title,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCreateApplication, useRequests, useWithdraw } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

const CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"];

export default function RequestsPage() {
  const { data, isPending, error } = useRequests();
  const create = useCreateApplication();
  const withdraw = useWithdraw();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    category: "CL",
    start_date: null as Date | null,
    end_date: null as Date | null,
    start_half: "full",
    end_half: "full",
    purpose: "",
    station_leave: false,
    destination: "",
  });

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const items: LeaveRequest[] = data?.results ?? [];

  function submit() {
    if (!form.start_date || !form.end_date) {
      notifications.show({ color: "red", title: "Dates required", message: "Pick the leave period." });
      return;
    }
    create.mutate(
      {
        category: form.category,
        start_date: form.start_date.toISOString().slice(0, 10),
        end_date: form.end_date.toISOString().slice(0, 10),
        start_half: form.start_half,
        end_half: form.end_half,
        purpose: form.purpose,
        station_leave: form.station_leave,
        station_details: form.station_leave
          ? { destination: form.destination }
          : {},
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Leave applied", message: "Your request is in the queue." });
          setOpen(false);
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not submit", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Your applications and their place in the approval chain"
        action={<Button onClick={() => setOpen(true)}>Apply for leave</Button>}
      />
      {isPending ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <Stack>
          {items.map((r) => (
            <Card key={r.id} withBorder radius="md" p="md">
              <Group justify="space-between">
                <Title order={5}>
                  {r.category} · {r.start_date} → {r.end_date} · {r.days} day(s)
                </Title>
                <StatusBadge status={r.status} />
              </Group>
              {r.purpose && <Text size="sm" c="dimmed">{r.purpose}</Text>}
              {r.recommendation && (
                <Text size="sm">
                  Unit Head: <b>{r.recommendation}</b> — {r.recommendation_reason}
                </Text>
              )}
              <Group mt="xs">
                {r.status !== "approved" && r.status !== "rejected"
                  && r.status !== "withdrawn" && (
                  <Button
                    size="xs" variant="light" color="red"
                    onClick={() => withdraw.mutate(
                      { id: r.id },
                      {
                        onSuccess: () => notifications.show({
                          color: "gray", title: "Withdrawn",
                          message: "The request was withdrawn.",
                        }),
                        onError: (e) => notifications.show({
                          color: "red", title: "Could not withdraw",
                          message: errorMessage(e),
                        }),
                      })}
                  >
                    Withdraw
                  </Button>
                )}
                <Badge variant="outline">{r.kind}</Badge>
                {r.station_leave && <Badge color="cyan" variant="light">Station leave</Badge>}
              </Group>
            </Card>
          ))}
          {items.length === 0 && <Text c="dimmed">No leave applications yet.</Text>}
        </Stack>
      )}

      <FormModal opened={open} onClose={() => setOpen(false)} title="Apply for leave"
        onSubmit={submit} submitLabel="Submit" submitting={create.isPending}>
        <Stack>
          <Select
            label="Category" data={CATEGORIES}
            value={form.category}
            onChange={(v) => setForm({ ...form, category: v ?? "CL" })}
          />
          <Group grow>
            <DateInput
              label="From" value={form.start_date}
              onChange={(d) => setForm({ ...form, start_date: d })}
            />
            <DateInput
              label="To" value={form.end_date}
              onChange={(d) => setForm({ ...form, end_date: d })}
            />
          </Group>
          <Group grow>
            <Select
              label="Start half" data={["full", "first", "second"]}
              value={form.start_half}
              onChange={(v) => setForm({ ...form, start_half: v ?? "full" })}
            />
            <Select
              label="End half" data={["full", "first", "second"]}
              value={form.end_half}
              onChange={(v) => setForm({ ...form, end_half: v ?? "full" })}
            />
          </Group>
          <Textarea
            label="Purpose" value={form.purpose}
            onChange={(e) => setForm({ ...form, purpose: e.target.value })}
          />
          <Checkbox
            label="Station leave (travel outside Jabalpur)"
            checked={form.station_leave}
            onChange={(e) => setForm({ ...form, station_leave: e.currentTarget.checked })}
          />
          {form.station_leave && (
            <TextInput
              label="Destination" value={form.destination}
              onChange={(e) => setForm({ ...form, destination: e.target.value })}
            />
          )}
        </Stack>
      </FormModal>
    </Container>
  );
}
