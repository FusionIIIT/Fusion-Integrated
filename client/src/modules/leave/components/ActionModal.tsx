import { useEffect, useState } from "react";
import { TextInput, Textarea } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { useRequestAction } from "../api/hooks";

export interface PendingAction {
  id: number;
  action: string;
  title: string;
  body?: Record<string, unknown>;
  /** A date the user must supply, sent under this key. */
  dateField?: string;
  /** A number the user must supply, sent under this key. */
  numberField?: string;
  textField?: string;
  danger?: boolean;
}

/** Confirms one request action, collecting at most a date, a number and a note. */
export function ActionModal({ pending, onClose }: {
  pending: PendingAction | null; onClose: () => void;
}) {
  const run = useRequestAction();
  const [date, setDate] = useState("");
  const [num, setNum] = useState("");
  const [text, setText] = useState("");
  useEffect(() => { setDate(""); setNum(""); setText(""); run.reset(); },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pending]);
  if (!pending) return null;
  const textKey = pending.textField ?? "note";
  const blocked = (pending.dateField && !date) || (pending.numberField && !num)
    || (pending.textField && !text.trim());

  function submit() {
    if (!pending) return;
    const body: Record<string, unknown> = { ...pending.body, [textKey]: text };
    if (pending.dateField) body[pending.dateField] = date;
    if (pending.numberField) body[pending.numberField] = Number(num);
    run.mutate({ id: pending.id, action: pending.action, body }, { onSuccess: onClose });
  }

  return (
    <FormModal opened onClose={onClose} title={pending.title} onSubmit={submit}
      submitLabel="Confirm" submitting={run.isPending} error={run.error}
      danger={pending.danger} disabled={Boolean(blocked)} size="md">
      {pending.dateField && (
        <TextInput type="date" label="Date" required value={date}
          onChange={(e) => setDate(e.currentTarget.value)} />
      )}
      {pending.numberField && (
        <TextInput label="Employee user id" required value={num} inputMode="numeric"
          onChange={(e) => setNum(e.currentTarget.value.replace(/\D/g, ""))} />
      )}
      <Textarea mt="sm" autosize minRows={2} required={Boolean(pending.textField)}
        label={pending.textField ? "Purpose" : "Note (optional)"} value={text}
        onChange={(e) => setText(e.currentTarget.value)} />
    </FormModal>
  );
}
