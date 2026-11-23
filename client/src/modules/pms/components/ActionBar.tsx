import { Button, Group } from "@mantine/core";
import { useState } from "react";

import { FieldsModal, type FieldSpec, type FieldValue } from "./FieldsModal";

export interface Runner<V> {
  mutate: (vars: V, options?: { onSuccess?: () => void }) => void;
  isPending: boolean;
  error: unknown;
  reset: () => void;
}

export interface Action {
  key: string;
  label: string;
  title: string;
  subtitle?: string;
  fields: FieldSpec[];
  submitLabel?: string;
  danger?: boolean;
  run: (values: Record<string, FieldValue>, done: () => void) => void;
  pending: boolean;
  error: unknown;
  reset: () => void;
}

// Bind a mutation to an action; the caller lists only the actions the acting role may take.
export function action<V>(spec: Omit<Action, "run" | "pending" | "error" | "reset">,
  runner: Runner<V>, toVars: (values: Record<string, FieldValue>) => V): Action {
  return {
    ...spec,
    run: (values, done) => runner.mutate(toVars(values), { onSuccess: done }),
    pending: runner.isPending,
    error: runner.error,
    reset: runner.reset,
  };
}

export function ActionBar({ actions }: { actions: Action[] }) {
  const [open, setOpen] = useState<string | null>(null);
  if (!actions.length) return null;
  const current = actions.find((a) => a.key === open);
  const close = () => {
    current?.reset();
    setOpen(null);
  };
  return (
    <>
      <Group gap="xs" wrap="wrap">
        {actions.map((a) => (
          <Button key={a.key} size="xs" variant={a.danger ? "light" : "filled"}
            color={a.danger ? "red" : undefined} onClick={() => setOpen(a.key)}>
            {a.label}
          </Button>
        ))}
      </Group>
      {current && (
        <FieldsModal
          opened title={current.title} subtitle={current.subtitle} fields={current.fields}
          submitLabel={current.submitLabel ?? current.label} danger={current.danger}
          submitting={current.pending} error={current.error} onClose={close}
          onSubmit={(values) => current.run(values, close)}
        />
      )}
    </>
  );
}

export const str = (v: FieldValue | undefined): string => (v == null ? "" : String(v));
export const num = (v: FieldValue | undefined): number => Number(v);
