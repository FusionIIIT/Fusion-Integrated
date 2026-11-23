import {
  Checkbox, MultiSelect, NumberInput, Select, Stack, Textarea, TextInput,
} from "@mantine/core";
import { useState } from "react";

import { FormModal } from "../../../ui/components/FormModal";
import { PersonPicker } from "./PersonPicker";

export type FieldValue = string | number | boolean | string[] | null;

export interface FieldSpec {
  name: string;
  label: string;
  type: "text" | "textarea" | "number" | "date" | "select" | "multiselect" | "checkbox"
    | "person";
  options?: { value: string; label: string }[];
  required?: boolean;
  initial?: FieldValue;
  description?: string;
  kind?: string;
}

interface Props {
  opened: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  fields: FieldSpec[];
  submitLabel: string;
  onSubmit: (values: Record<string, FieldValue>) => void;
  submitting?: boolean;
  error?: unknown;
  danger?: boolean;
}

// A form described by its fields; the server's refusal is shown inside it as sent.
export function FieldsModal(props: Props) {
  // Mounted only while open, so every opening starts from the initial values.
  return props.opened ? <OpenForm {...props} /> : null;
}

function OpenForm({ opened, onClose, title, subtitle, fields, submitLabel, onSubmit,
  submitting, error, danger }: Props) {
  const [values, setValues] = useState<Record<string, FieldValue>>(() =>
    Object.fromEntries(fields.map((f) => [f.name, f.initial
      ?? (f.type === "checkbox" ? false : f.type === "multiselect" ? [] : null)])));

  const set = (name: string, v: FieldValue) => setValues((s) => ({ ...s, [name]: v }));
  const missing = fields.filter((f) => f.required && (values[f.name] === null
    || values[f.name] === "" || (Array.isArray(values[f.name])
      && (values[f.name] as string[]).length === 0)));

  return (
    <FormModal
      opened={opened} onClose={onClose} title={title} subtitle={subtitle}
      submitLabel={submitLabel} submitting={submitting} error={error} danger={danger}
      disabled={missing.length > 0}
      disabledReason={missing.length ? `Fill in: ${missing.map((f) => f.label).join(", ")}` : ""}
      onSubmit={() => onSubmit(values)}
    >
      <Stack gap="sm">
        {fields.map((f) => {
          const common = { label: f.label, required: f.required,
            description: f.description };
          const v = values[f.name];
          switch (f.type) {
            case "textarea":
              return <Textarea key={f.name} {...common} autosize minRows={3} value={String(v ?? "")}
                onChange={(e) => set(f.name, e.currentTarget.value)} />;
            case "number":
              return <NumberInput key={f.name} {...common} value={v == null ? "" : Number(v)}
                onChange={(n) => set(f.name, n === "" ? null : Number(n))} />;
            case "date":
              return <TextInput key={f.name} {...common} type="date" value={String(v ?? "")}
                onChange={(e) => set(f.name, e.currentTarget.value)} />;
            case "select":
              return <Select key={f.name} {...common} allowDeselect={!f.required}
                data={f.options ?? []} value={(v as string) ?? null}
                onChange={(s) => set(f.name, s)} />;
            case "multiselect":
              return <MultiSelect key={f.name} {...common} searchable data={f.options ?? []}
                value={(v as string[]) ?? []} onChange={(s) => set(f.name, s)} />;
            case "checkbox":
              return <Checkbox key={f.name} label={f.label} checked={Boolean(v)}
                onChange={(e) => set(f.name, e.currentTarget.checked)} />;
            case "person":
              return <PersonPicker key={f.name} label={f.label} required={f.required}
                kind={f.kind} value={(v as number | null) ?? null}
                onChange={(id) => set(f.name, id)} />;
            default:
              return <TextInput key={f.name} {...common} value={String(v ?? "")}
                onChange={(e) => set(f.name, e.currentTarget.value)} />;
          }
        })}
      </Stack>
    </FormModal>
  );
}
