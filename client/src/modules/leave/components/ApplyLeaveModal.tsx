import { useState } from "react";
import {
  Checkbox, Group, Select, SimpleGrid, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { FormModal } from "../../../ui/components/FormModal";
import { useApply, useEmployees } from "../api/hooks";
import type { ApplyInput, Category, Half } from "../api/types";

const CATEGORIES: { value: Category; label: string }[] = [
  { value: "CL", label: "Casual Leave" }, { value: "RH", label: "Restricted Holiday" },
  { value: "SCL", label: "Special Casual Leave" }, { value: "EL", label: "Earned Leave" },
  { value: "COL", label: "Commuted Leave" }, { value: "VL", label: "Vacation Leave" },
];

const EMPTY: ApplyInput = {
  category: "CL", start_date: "", end_date: "", half: "full", purpose: "",
  substitute_user_id: null, station_leave: false, station_address: "",
  medical_evidence_ref: "",
};

/** EL-UC-001. Station Leave lives inside the same form (BR-EL-013). */
export function ApplyLeaveModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [form, setForm] = useState<ApplyInput>(EMPTY);
  const [search, setSearch] = useState("");
  const employees = useEmployees(search);
  const apply = useApply();
  const set = (patch: Partial<ApplyInput>) => setForm((f) => ({ ...f, ...patch }));
  const halfAllowed = form.category === "CL" && form.start_date === form.end_date;
  const missing = !form.start_date || !form.end_date || !form.purpose.trim();

  function submit() {
    apply.mutate({ ...form, half: halfAllowed ? form.half : "full" }, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Leave submitted",
          message: "You can follow its progress in your request list." });
        setForm(EMPTY);
        onClose();
      },
    });
  }

  return (
    <FormModal
      opened={opened} onClose={onClose} title="Apply for leave"
      subtitle="A submitted request cannot be edited; withdraw and re-apply instead."
      onSubmit={submit} submitLabel="Submit" submitting={apply.isPending}
      error={apply.error} disabled={missing}
      disabledReason={missing ? "Dates and purpose are required." : undefined}
    >
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <Select label="Category" data={CATEGORIES} value={form.category} allowDeselect={false}
          onChange={(v) => set({ category: (v ?? "CL") as Category })} />
        <Select label="Day" disabled={!halfAllowed} value={halfAllowed ? form.half : "full"}
          data={[{ value: "full", label: "Full day" }, { value: "first", label: "First half" },
            { value: "second", label: "Second half" }]}
          onChange={(v) => set({ half: (v ?? "full") as Half })} />
        <TextInput type="date" label="From" value={form.start_date} required
          onChange={(e) => set({ start_date: e.currentTarget.value })} />
        <TextInput type="date" label="To" value={form.end_date} required
          onChange={(e) => set({ end_date: e.currentTarget.value })} />
      </SimpleGrid>
      <Textarea label="Purpose" mt="sm" required autosize minRows={2} value={form.purpose}
        onChange={(e) => set({ purpose: e.currentTarget.value })} />
      <Select
        label="Substitute (responsibility holder)" mt="sm" clearable searchable
        placeholder="Only if your duties need cover"
        searchValue={search} onSearchChange={setSearch}
        data={(employees.data ?? []).map((e) => ({
          value: String(e.user_id), label: `${e.display_name} · ${e.department || e.kind}` }))}
        value={form.substitute_user_id ? String(form.substitute_user_id) : null}
        onChange={(v) => set({ substitute_user_id: v ? Number(v) : null })}
      />
      {form.category === "COL" && (
        <TextInput label="Medical evidence reference" mt="sm"
          value={form.medical_evidence_ref}
          onChange={(e) => set({ medical_evidence_ref: e.currentTarget.value })} />
      )}
      <Group mt="md">
        <Checkbox label="I will be away from Jabalpur (Station Leave)"
          checked={form.station_leave}
          onChange={(e) => set({ station_leave: e.currentTarget.checked })} />
      </Group>
      {form.station_leave && (
        <TextInput label="Address while away" mt="sm" required value={form.station_address}
          onChange={(e) => set({ station_address: e.currentTarget.value })} />
      )}
    </FormModal>
  );
}
