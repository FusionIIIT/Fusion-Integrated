import {
  Checkbox, Group, Select, SimpleGrid, Stack, Textarea, TextInput,
} from "@mantine/core";

import { CATEGORY_LABELS, type Category, type LeaveInput } from "../api/types";
import { EmployeePicker } from "./EmployeePicker";

export const EMPTY_LEAVE: LeaveInput = {
  category: "CL", start_date: "", end_date: "", half: "", purpose: "",
  medical_evidence: "", station_leave: false, station_from: null, station_to: null,
  station_address: "", substitute_user_id: null, responsibility: "",
};

export function missingReason(v: LeaveInput): string {
  if (!v.start_date || !v.end_date) return "Choose the leave dates.";
  if (!v.purpose.trim()) return "Give the purpose of the leave.";
  if (v.station_leave && (!v.station_from || !v.station_to || !v.station_address.trim())) {
    return "Station Leave needs the dates away and an address.";
  }
  return "";
}

/** One form for apply and modify, so the two can never ask different questions. */
export function LeaveForm({ value, onChange }: {
  value: LeaveInput;
  onChange: (v: LeaveInput) => void;
}) {
  const set = <K extends keyof LeaveInput>(k: K, v: LeaveInput[K]) =>
    onChange({ ...value, [k]: v });
  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Select
          label="Leave category" required allowDeselect={false}
          data={Object.entries(CATEGORY_LABELS).map(([k, l]) => ({ value: k, label: l }))}
          value={value.category}
          onChange={(c) => onChange({ ...value, category: (c ?? "CL") as Category,
            half: c === "CL" ? value.half : "" })}
        />
        {value.category === "CL" && (
          <Select
            label="Half day" clearable placeholder="Full day"
            data={[{ value: "first", label: "First half" },
              { value: "second", label: "Second half" }]}
            value={value.half || null}
            onChange={(h) => onChange({ ...value, half: (h ?? "") as LeaveInput["half"],
              end_date: h ? value.start_date : value.end_date })}
          />
        )}
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <TextInput
          type="date" label="From" required value={value.start_date}
          onChange={(e) => onChange({ ...value, start_date: e.currentTarget.value,
            end_date: value.half ? e.currentTarget.value : value.end_date })}
        />
        <TextInput
          type="date" label="To" required value={value.end_date} disabled={!!value.half}
          onChange={(e) => set("end_date", e.currentTarget.value)}
        />
      </SimpleGrid>
      <Textarea
        label="Purpose / reason" required autosize minRows={2} value={value.purpose}
        onChange={(e) => set("purpose", e.currentTarget.value)}
      />
      {value.category === "COL" && (
        <TextInput
          label="Medical certificate reference" value={value.medical_evidence}
          description="Commuted Leave is medical leave and needs supporting evidence."
          onChange={(e) => set("medical_evidence", e.currentTarget.value)}
        />
      )}
      <Checkbox
        label="I will be outside Jabalpur (Station Leave)" checked={value.station_leave}
        onChange={(e) => set("station_leave", e.currentTarget.checked)}
      />
      {value.station_leave && (
        <Stack gap="sm">
          <Group grow>
            <TextInput
              type="date" label="Away from" value={value.station_from ?? ""}
              onChange={(e) => set("station_from", e.currentTarget.value || null)}
            />
            <TextInput
              type="date" label="Away until" value={value.station_to ?? ""}
              onChange={(e) => set("station_to", e.currentTarget.value || null)}
            />
          </Group>
          <TextInput
            label="Address while away" value={value.station_address}
            onChange={(e) => set("station_address", e.currentTarget.value)}
          />
        </Stack>
      )}
      <EmployeePicker
        label="Substitute (optional)" value={value.substitute_user_id}
        description="If you nominate someone, your request waits for their consent."
        onChange={(id) => set("substitute_user_id", id)}
      />
      {value.substitute_user_id != null && (
        <TextInput
          label="Responsibility to cover" value={value.responsibility}
          onChange={(e) => set("responsibility", e.currentTarget.value)}
        />
      )}
    </Stack>
  );
}
