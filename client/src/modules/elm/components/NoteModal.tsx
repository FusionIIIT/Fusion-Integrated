import { Textarea } from "@mantine/core";
import { useEffect, useState } from "react";

import { FormModal } from "../../../ui/components/FormModal";

/** A confirmation that may carry a reason; `required` blocks an empty one. */
export function NoteModal({ opened, title, subtitle, label, required, submitLabel, danger,
  submitting, error, onClose, onSubmit, children }: {
  opened: boolean;
  title: string;
  subtitle?: string;
  label: string;
  required?: boolean;
  submitLabel: string;
  danger?: boolean;
  submitting?: boolean;
  error?: unknown;
  onClose: () => void;
  onSubmit: (note: string) => void;
  children?: React.ReactNode;
}) {
  const [note, setNote] = useState("");
  useEffect(() => { if (opened) setNote(""); }, [opened]);
  return (
    <FormModal
      opened={opened} onClose={onClose} title={title} subtitle={subtitle}
      onSubmit={() => onSubmit(note)} submitLabel={submitLabel} danger={danger}
      submitting={submitting} error={error} size="md"
      disabled={required && !note.trim()} disabledReason="A reason is required."
    >
      {children}
      <Textarea label={label} autosize minRows={2} value={note}
        onChange={(e) => setNote(e.currentTarget.value)} required={required} />
    </FormModal>
  );
}
