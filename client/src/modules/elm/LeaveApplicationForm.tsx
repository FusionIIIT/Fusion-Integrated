import { useState } from "react";
import {
  Alert, Button, Checkbox, Group, SegmentedControl, Select, SimpleGrid, Stack,
  Textarea, TextInput,
} from "@mantine/core";

import { errorMessage } from "../../lib/http";
import type { HalfDay, LeaveApplication, LeaveCategory } from "./api/types";
import { CATEGORY_LABELS } from "./api/types";

const EMPTY: LeaveApplication = {
  category: "CL", start_date: "", end_date: "", half: "", reason: "",
  is_station_leave: false, station_address: "", station_contact: "",
};

/** The one leave form. Station Leave is a section of it, not a separate
 *  request (BR-EL-013). The server re-checks every rule; the client only
 *  stops obviously incomplete submissions. */
export function LeaveApplicationForm({ onSubmit, submitting, error }: {
  onSubmit: (body: LeaveApplication, reset: () => void) => void;
  submitting?: boolean;
  error?: unknown;
}) {
  const [form, setForm] = useState<LeaveApplication>(EMPTY);
  const set = <K extends keyof LeaveApplication>(k: K, v: LeaveApplication[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const halfDay = form.category === "CL" && form.half !== "";
  const incomplete = !form.start_date || !(halfDay || form.end_date) ||
    !form.reason.trim() ||
    (form.is_station_leave &&
      !(form.station_address.trim() && form.station_contact.trim()));

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = halfDay ? { ...form, end_date: form.start_date } : form;
    onSubmit(body, () => setForm(EMPTY));
  }

  return (
    <form onSubmit={submit}>
      <Stack>
        {error ? <Alert color="red">{errorMessage(error)}</Alert> : null}
        <Select
          label="Leave category" required allowDeselect={false}
          data={Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
            value, label: `${label} (${value})`,
          }))}
          value={form.category}
          onChange={(v) => setForm((f) => ({
            ...f, category: (v ?? "CL") as LeaveCategory,
            half: v === "CL" ? f.half : "",
          }))}
        />
        {form.category === "CL" && (
          <SegmentedControl
            value={form.half}
            onChange={(v) => set("half", v as HalfDay)}
            data={[
              { value: "", label: "Full day(s)" },
              { value: "first", label: "First half" },
              { value: "second", label: "Second half" },
            ]}
          />
        )}
        <SimpleGrid cols={{ base: 1, sm: 2 }}>
          <TextInput
            type="date" label={halfDay ? "Date" : "From"} required
            value={form.start_date}
            onChange={(e) => set("start_date", e.currentTarget.value)}
          />
          {!halfDay && (
            <TextInput
              type="date" label="To" required min={form.start_date || undefined}
              value={form.end_date}
              onChange={(e) => set("end_date", e.currentTarget.value)}
            />
          )}
        </SimpleGrid>
        <Textarea
          label="Reason" required autosize minRows={2} maxLength={2000}
          value={form.reason}
          onChange={(e) => set("reason", e.currentTarget.value)}
        />
        <Checkbox
          label="I will be away from the station (Station Leave)"
          checked={form.is_station_leave}
          onChange={(e) => set("is_station_leave", e.currentTarget.checked)}
        />
        {form.is_station_leave && (
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput
              label="Address while away" required maxLength={300}
              value={form.station_address}
              onChange={(e) => set("station_address", e.currentTarget.value)}
            />
            <TextInput
              label="Contact number while away" required maxLength={30}
              value={form.station_contact}
              onChange={(e) => set("station_contact", e.currentTarget.value)}
            />
          </SimpleGrid>
        )}
        <Group justify="flex-end">
          <Button type="submit" loading={submitting} disabled={incomplete}>
            Submit application
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
