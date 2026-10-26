import { useEffect, useState } from "react";
import {
  Button, Card, Checkbox, Container, Group, NumberInput, SimpleGrid, Stack,
  Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { useCalendars, usePolicy, usePublishCalendar, useSavePolicy } from "../api/hooks";
import type { LeavePolicy } from "../api/types";

const AdministrationPage = () => {
  const policyQ = usePolicy();
  const save = useSavePolicy();
  const calendars = useCalendars();
  const publish = usePublishCalendar();
  const [draft, setDraft] = useState<LeavePolicy | null>(null);
  useEffect(() => { if (policyQ.data) setDraft(policyQ.data); }, [policyQ.data]);

  if (policyQ.error) return <ErrorState error={policyQ.error} />;
  if (!draft) return <Text c="dimmed">Loading policy…</Text>;

  return (
    <Container size="lg">
      <PageHeader title="Leave Administration" subtitle="Policy and calendar configuration" />
      <h3>Leave policy</h3>
      <Card>
        <Stack gap="md">
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            <NumberInput
              label="CL Days"
              value={draft.cl_days}
              onChange={(v) => setDraft({ ...draft, cl_days: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="RH Days"
              value={draft.rh_days}
              onChange={(v) => setDraft({ ...draft, rh_days: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="SCL Days"
              value={draft.scl_days}
              onChange={(v) => setDraft({ ...draft, scl_days: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="EL Days"
              value={draft.el_days}
              onChange={(v) => setDraft({ ...draft, el_days: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="VL Days"
              value={draft.vl_days}
              onChange={(v) => setDraft({ ...draft, vl_days: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="COL Days"
              value={draft.col_days}
              onChange={(v) => setDraft({ ...draft, col_days: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="VL per EL"
              value={draft.vl_per_el}
              onChange={(v) => setDraft({ ...draft, vl_per_el: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="Reminder Hours"
              value={draft.reminder_hours}
              onChange={(v) => setDraft({ ...draft, reminder_hours: typeof v === "number" ? v : 0 })}
            />
            <NumberInput
              label="Escalation Hours"
              value={draft.escalation_hours}
              onChange={(v) => setDraft({ ...draft, escalation_hours: typeof v === "number" ? v : 0 })}
            />
          </SimpleGrid>
          <TextInput
            label="Label"
            value={draft.label}
            onChange={(e) => setDraft({ ...draft, label: e.currentTarget.value })}
          />
          <TextInput
            label="Year Label"
            value={draft.year_label}
            onChange={(e) => setDraft({ ...draft, year_label: e.currentTarget.value })}
          />
          <TextInput
            label="Authority Path"
            value={draft.authority_path}
            onChange={(e) => setDraft({ ...draft, authority_path: e.currentTarget.value })}
          />
          <TextInput
            label="Establishment Designation"
            value={draft.establishment_designation}
            onChange={(e) => setDraft({ ...draft, establishment_designation: e.currentTarget.value })}
          />
          <TextInput
            label="Starts On"
            type="date"
            value={draft.starts_on}
            onChange={(e) => setDraft({ ...draft, starts_on: e.currentTarget.value })}
          />
          <TextInput
            label="Ends On"
            type="date"
            value={draft.ends_on}
            onChange={(e) => setDraft({ ...draft, ends_on: e.currentTarget.value })}
          />
          <TextInput
            label="Year End On"
            type="date"
            value={draft.year_end_on ?? ""}
            onChange={(e) => setDraft({ ...draft, year_end_on: e.currentTarget.value })}
          />
          <Checkbox
            label="Establishment Step Enabled"
            checked={draft.establishment_step_enabled}
            onChange={(e) => setDraft({ ...draft, establishment_step_enabled: e.currentTarget.checked })}
          />
          <Button
            onClick={() => save.mutate(draft, {
              onSuccess: () => notifications.show({ color: "green", title: "Policy saved", message: "The leave policy has been updated." }),
              onError: (e) => notifications.show({ color: "red", title: "Could not save", message: errorMessage(e) }),
            })}
            loading={save.isPending}
          >
            Save
          </Button>
        </Stack>
      </Card>
      <h3>Calendars</h3>
      <Stack gap="xs">
        {calendars.data?.results.map(c => (
          <Card key={c.id} padding="md">
            <Group justify="space-between">
              <Text fw={600}>{c.year_label} — {c.label || "Calendar"}</Text>
              <Text size="sm" c="dimmed">{c.published_at ? `Published ${c.published_at}` : "Draft"}</Text>
              <Button size="xs" disabled={Boolean(c.published_at)} loading={publish.isPending} onClick={() => publish.mutate(c.id)}>
                Publish
              </Button>
            </Group>
          </Card>
        ))}
        {calendars.data?.results.length === 0 && <Text c="dimmed">No calendars yet.</Text>}
      </Stack>
    </Container>
  );
};

export default AdministrationPage;
