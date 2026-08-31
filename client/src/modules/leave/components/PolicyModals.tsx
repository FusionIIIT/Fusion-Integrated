import { useState } from "react";
import { NumberInput, Stack, Textarea, TextInput } from "@mantine/core";
import { DateInput } from "@mantine/dates";

import { FormModal } from "../../../ui/components/FormModal";

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** A version is drafted, filled in, and only then published. Nothing here puts
 *  anything into force — that is a separate, deliberate action. */
export function NewPolicyModal({ opened, onClose, onSubmit, submitting }: {
  opened: boolean;
  onClose: () => void;
  onSubmit: (body: {
    version: string; effective_from: string; note: string;
    max_backdate_days: number;
  }) => void;
  submitting?: boolean;
}) {
  const [version, setVersion] = useState("");
  const [from, setFrom] = useState<Date | null>(null);
  const [note, setNote] = useState("");
  const [backdate, setBackdate] = useState<number | string>(0);

  const incomplete = !version.trim() || !from;

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="New policy version"
      subtitle="Drafted, not in force. Add its rules, then publish it."
      submitLabel="Create draft"
      submitting={submitting}
      disabled={incomplete}
      disabledReason={incomplete ? "A version and an effective date are needed." : undefined}
      onSubmit={() => {
        if (!from) return;
        onSubmit({
          version: version.trim(), effective_from: iso(from), note: note.trim(),
          max_backdate_days: Number(backdate) || 0,
        });
        setVersion(""); setFrom(null); setNote(""); setBackdate(0);
      }}
    >
      <Stack gap="sm">
        <TextInput
          label="Version" placeholder="2027.1" value={version}
          onChange={(e) => setVersion(e.currentTarget.value)}
        />
        <DateInput label="In force from" value={from} onChange={setFrom} />
        <NumberInput
          label="Days an application may reach back"
          description="Zero means none. Leave already taken is recorded by the administrator instead."
          min={0} value={backdate} onChange={setBackdate}
        />
        <Textarea
          label="Note" autosize minRows={2} value={note}
          onChange={(e) => setNote(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}

export function NewCalendarModal({ opened, onClose, onSubmit, submitting }: {
  opened: boolean;
  onClose: () => void;
  onSubmit: (body: { year: number; version: string }) => void;
  submitting?: boolean;
}) {
  const [year, setYear] = useState<number | string>(new Date().getFullYear());
  const [version, setVersion] = useState("1");

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="New calendar"
      subtitle="Add its holidays and vacation periods, then publish it."
      submitLabel="Create draft"
      submitting={submitting}
      disabled={!version.trim()}
      onSubmit={() => onSubmit({ year: Number(year), version: version.trim() })}
    >
      <Stack gap="sm">
        <NumberInput label="Year" min={2000} max={2200} value={year} onChange={setYear} />
        <TextInput
          label="Version" value={version}
          onChange={(e) => setVersion(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
