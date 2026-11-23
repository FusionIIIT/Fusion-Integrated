import { useState } from "react";
import {
  ActionIcon, Button, Card, Center, Group, Loader, Select, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { FaPlus, FaTrash } from "react-icons/fa";

import { ErrorState } from "../../../../ui/components/ErrorState";
import { FormModal } from "../../../../ui/components/FormModal";
import { useCreatePoll, usePollOptions, usePolls } from "../../api/hooks";
import type { LedClub, PollGroup } from "../../api/types";
import { PollTally } from "../../pages/PollsPage";
import { dateTime } from "../format";
import { LoadMore } from "../LoadMore";
import { done } from "../toasts";

export function PollsPanel({ club }: { club: LedClub }) {
  const list = usePolls({ club_id: club.id });
  const [creating, setCreating] = useState(false);
  if (list.error) return <ErrorState error={list.error} />;
  return (
    <>
      <Button mb="md" onClick={() => setCreating(true)}>Create poll</Button>
      {list.loading ? (
        <Center py="xl"><Loader size="sm" aria-label="Loading polls" /></Center>
      ) : list.rows.length === 0 ? (
        <Text ta="center" c="dimmed">No polls yet.</Text>
      ) : (
        <Stack gap="md">
          {list.rows.map((p) => (
            <Card key={p.id} withBorder component="section" aria-label={p.title}>
              <Text fw={600}>{p.title}</Text>
              <Text size="sm" c="dimmed">
                {p.target_groups.map((g) => `${g.batch} / ${g.branch}`).join(", ")}
                {" · "}closes {dateTime(p.expires_at)}
              </Text>
              <PollTally poll={p} />
            </Card>
          ))}
        </Stack>
      )}
      <LoadMore list={list} />
      {creating && <CreatePollModal club={club} onClose={() => setCreating(false)} />}
    </>
  );
}

function CreatePollModal({ club, onClose }: { club: LedClub; onClose: () => void }) {
  const create = useCreatePoll();
  const options = usePollOptions(true);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [expires, setExpires] = useState("");
  const [choices, setChoices] = useState(["", ""]);
  const [groups, setGroups] = useState<PollGroup[]>([]);
  const [batch, setBatch] = useState<string | null>(null);
  const [branch, setBranch] = useState<string | null>(null);

  const filled = choices.map((c) => c.trim()).filter(Boolean);
  const addGroup = () => {
    if (!batch || !branch) return;
    if (!groups.some((g) => g.batch === batch && g.branch === branch)) {
      setGroups([...groups, { batch, branch }]);
    }
    setBatch(null);
    setBranch(null);
  };
  const every = (label: string) => ({ value: "all", label });

  return (
    <FormModal
      opened onClose={onClose} title="Create poll" subtitle={club.name} submitLabel="Create"
      submitting={create.isPending} error={create.error ?? options.error}
      disabled={!title.trim() || !expires || filled.length < 2 || groups.length === 0}
      disabledReason="Give a title, a closing time, two choices and one target group."
      onSubmit={() => create.mutate({
        club_id: club.id, title, description, choices: filled, target_groups: groups,
        expires_at: new Date(expires).toISOString(),
      }, {
        onSuccess: () => {
          done("Poll created", `${title} is open to its target groups.`);
          onClose();
        },
      })}
    >
      <Stack gap="md">
        <TextInput label="Title" required maxLength={200} value={title}
          onChange={(e) => setTitle(e.currentTarget.value)} />
        <Textarea label="Poll description" autosize minRows={2} value={description}
          onChange={(e) => setDescription(e.currentTarget.value)} />
        <TextInput label="Closes at" type="datetime-local" required value={expires}
          onChange={(e) => setExpires(e.currentTarget.value)} />
        {choices.map((c, i) => (
          <TextInput key={i} label={`Choice ${i + 1}`} required={i < 2} maxLength={200} value={c}
            onChange={(e) => {
              const value = e.currentTarget.value;
              setChoices(choices.map((old, j) => (j === i ? value : old)));
            }} />
        ))}
        <Button variant="default" leftSection={<FaPlus size={10} />}
          onClick={() => setChoices([...choices, ""])}>
          Add choice
        </Button>
        <Group align="flex-end" grow>
          <Select label="Batch" value={batch} onChange={setBatch}
            data={[every("All batches"),
              ...(options.data?.batches ?? []).map((b) => ({ value: b, label: b }))]} />
          <Select label="Branch" value={branch} onChange={setBranch}
            data={[every("All branches"),
              ...(options.data?.branches ?? []).map((b) => ({ value: b, label: b }))]} />
          <Button variant="default" onClick={addGroup} disabled={!batch || !branch}>
            Add group
          </Button>
        </Group>
        {groups.map((g) => (
          <Group key={`${g.batch}/${g.branch}`} justify="space-between">
            <Text size="sm">{g.batch} / {g.branch}</Text>
            <ActionIcon variant="subtle" color="red"
              aria-label={`Remove group ${g.batch} / ${g.branch}`}
              onClick={() => setGroups(groups.filter((x) => x !== g))}>
              <FaTrash size={12} />
            </ActionIcon>
          </Group>
        ))}
      </Stack>
    </FormModal>
  );
}
