import { ActionIcon, Button, Group, Stack, Switch, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { FaTrash } from "react-icons/fa";

import { FormModal } from "../../../ui/components/FormModal";
import { useReplaceInventors } from "../api/hooks";
import type { Inventor } from "../api/types";
import { PersonPicker } from "./PersonPicker";

interface Row {
  user_id: number | null;
  name: string;
  affiliation: string;
  email: string;
  share_percent: string;
  external: boolean;
}

function fromInventor(i: Inventor): Row {
  return { user_id: i.user_id, name: i.name, affiliation: i.affiliation, email: i.email,
    share_percent: i.share_percent, external: i.user_id == null };
}

// UC-PMS-003: the whole inventor set is sent at once so the 100% total is checked together.
export function InventorsModal({ applicationId, inventors, onClose }: {
  applicationId: number;
  inventors: Inventor[];
  onClose: () => void;
}) {
  const save = useReplaceInventors();
  const [rows, setRows] = useState<Row[]>(inventors.length ? inventors.map(fromInventor) : [
    { user_id: null, name: "", affiliation: "", email: "", share_percent: "100",
      external: false }]);
  const total = rows.reduce((s, r) => s + (Number(r.share_percent) || 0), 0);
  const update = (i: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <FormModal
      opened onClose={onClose} title="Inventors and ownership shares"
      subtitle={`Shares must add up to exactly 100 (now ${total.toFixed(2)}).`}
      submitLabel="Save inventors" submitting={save.isPending} error={save.error}
      onSubmit={() => save.mutate({
        id: applicationId,
        inventors: rows.map((r) => (r.external
          ? { name: r.name, affiliation: r.affiliation, email: r.email,
            share_percent: r.share_percent }
          : { user_id: r.user_id, share_percent: r.share_percent })),
      }, { onSuccess: onClose })}
    >
      <Stack gap="md">
        {rows.map((r, i) => (
          <Stack key={i} gap={6} p="sm" style={{ border: "1px solid var(--mantine-color-gray-3)",
            borderRadius: 8 }}>
            <Group justify="space-between">
              <Text fw={600} size="sm">Inventor {i + 1}</Text>
              <ActionIcon variant="subtle" color="red" aria-label={`Remove inventor ${i + 1}`}
                onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))}>
                <FaTrash size={12} />
              </ActionIcon>
            </Group>
            <Switch label="Not an institute member" checked={r.external}
              onChange={(e) => update(i, { external: e.currentTarget.checked, user_id: null })} />
            {r.external ? (
              <>
                <TextInput label="Name" required value={r.name}
                  onChange={(e) => update(i, { name: e.currentTarget.value })} />
                <TextInput label="Affiliation" required value={r.affiliation}
                  onChange={(e) => update(i, { affiliation: e.currentTarget.value })} />
                <TextInput label="Email" value={r.email}
                  onChange={(e) => update(i, { email: e.currentTarget.value })} />
              </>
            ) : (
              <PersonPicker label="Institute member" required value={r.user_id} name={r.name}
                onChange={(id, name) => update(i, { user_id: id, name })} />
            )}
            <TextInput label="Ownership share (%)" required value={r.share_percent}
              onChange={(e) => update(i, { share_percent: e.currentTarget.value })} />
          </Stack>
        ))}
        <Button variant="light" onClick={() => setRows((rs) => [...rs, { user_id: null, name: "",
          affiliation: "", email: "", share_percent: "", external: false }])}>
          Add inventor
        </Button>
      </Stack>
    </FormModal>
  );
}
