import { useState } from "react";
import {
  ActionIcon, Button, Group, NumberInput, Stack, Textarea, TextInput,
} from "@mantine/core";
import { FaTrash } from "react-icons/fa";

import { FormModal } from "../../../ui/components/FormModal";
import {
  useChangeLeadership, useCreatePoll, useSubmitBudget, useSubmitReport,
} from "../api/hooks";
import type { Club, Target } from "../api/types";
import { notifyDone } from "./notify";
import { PersonPicker } from "./PersonPicker";

interface FormProps { club: Club; onClose: () => void }

/** UC-GYM-008. */
export function LeadershipForm({ club, onClose }: FormProps) {
  const change = useChangeLeadership();
  const [coord, setCoord] = useState<number | null>(club.leaders.coordinator ?? null);
  const [co, setCo] = useState<number | null>(club.leaders.co_coordinator ?? null);
  return (
    <FormModal opened onClose={onClose} title={`Change leadership of ${club.name}`}
      subtitle="Both must be students; the current leaders stop being leaders"
      submitLabel="Change leadership" submitting={change.isPending} error={change.error}
      disabled={coord === null || co === null} disabledReason="Choose both leaders."
      onSubmit={() => coord !== null && co !== null && change.mutate(
        { clubId: club.id, coordinator_user_id: coord, co_coordinator_user_id: co },
        { onSuccess: () => { notifyDone("Leadership changed", club.name); onClose(); } })}>
      <PersonPicker label="New coordinator" kind="student" value={coord} onChange={setCoord}
        initialLabel={club.leader_names.coordinator} required />
      <PersonPicker label="New co-coordinator" kind="student" value={co} onChange={setCo}
        initialLabel={club.leader_names.co_coordinator} required />
    </FormModal>
  );
}

/** UC-GYM-006. */
export function PollForm({ club, onClose }: FormProps) {
  const create = useCreatePoll();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [expires, setExpires] = useState("");
  const [choices, setChoices] = useState(["", ""]);
  const [targets, setTargets] = useState<Target[]>([{ batch_year: 2024, discipline: "" }]);
  const missing = !title.trim() || !description.trim() || !expires
    || choices.filter((c) => c.trim()).length < 2 || targets.length === 0;

  const setChoice = (i: number, v: string) =>
    setChoices((cs) => cs.map((c, j) => (j === i ? v : c)));
  const setTarget = (i: number, t: Partial<Target>) =>
    setTargets((ts) => ts.map((x, j) => (j === i ? { ...x, ...t } : x)));

  return (
    <FormModal opened onClose={onClose} title={`New poll for ${club.name}`}
      subtitle="Addressed to the batches and branches you choose"
      submitLabel="Create poll" submitting={create.isPending} error={create.error}
      disabled={missing} disabledReason="Title, description, expiry, two choices and a group."
      onSubmit={() => create.mutate({ club_id: club.id, title, description,
        expires_on: expires, choices: choices.filter((c) => c.trim()), targets },
      { onSuccess: () => { notifyDone("Poll created", "The audience is being notified.");
        onClose(); } })}>
      <TextInput label="Title" required maxLength={200} value={title}
        onChange={(e) => setTitle(e.currentTarget.value)} />
      <Textarea mt="sm" label="Description" required autosize minRows={2} maxLength={4000}
        value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <TextInput mt="sm" type="date" label="Open until (inclusive)" required value={expires}
        onChange={(e) => setExpires(e.currentTarget.value)} />
      <Stack mt="sm" gap="xs">
        {choices.map((c, i) => (
          <Group key={i} wrap="nowrap" align="flex-end">
            <TextInput style={{ flex: 1 }} label={`Choice ${i + 1}`} maxLength={200} value={c}
              onChange={(e) => setChoice(i, e.currentTarget.value)} />
            <ActionIcon variant="subtle" color="red" aria-label={`Remove choice ${i + 1}`}
              disabled={choices.length <= 2}
              onClick={() => setChoices((cs) => cs.filter((_, j) => j !== i))}>
              <FaTrash size={12} /></ActionIcon>
          </Group>))}
        <Group><Button variant="subtle" size="xs" disabled={choices.length >= 10}
          onClick={() => setChoices((cs) => [...cs, ""])}>Add choice</Button></Group>
      </Stack>
      <Stack mt="sm" gap="xs">
        {targets.map((t, i) => (
          <Group key={i} wrap="nowrap" align="flex-end">
            <NumberInput label={`Batch ${i + 1}`} min={2000} max={2100} value={t.batch_year}
              onChange={(v) => setTarget(i, { batch_year: Number(v) || 0 })} />
            <TextInput style={{ flex: 1 }} label="Branch (empty for all branches)"
              maxLength={40} value={t.discipline}
              onChange={(e) => setTarget(i, { discipline: e.currentTarget.value })} />
            <ActionIcon variant="subtle" color="red" aria-label={`Remove group ${i + 1}`}
              disabled={targets.length <= 1}
              onClick={() => setTargets((ts) => ts.filter((_, j) => j !== i))}>
              <FaTrash size={12} /></ActionIcon>
          </Group>))}
        <Group><Button variant="subtle" size="xs" disabled={targets.length >= 20}
          onClick={() => setTargets((ts) => [...ts, { batch_year: 2024, discipline: "" }])}>
          Add group</Button></Group>
      </Stack>
    </FormModal>
  );
}

/** UC-GYM-009. */
export function BudgetForm({ club, onClose }: FormProps) {
  const submit = useSubmitBudget();
  const [purpose, setPurpose] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState<string | number>("");
  const [link, setLink] = useState("");
  const missing = !purpose.trim() || !description.trim() || amount === "" || !link.trim();
  return (
    <FormModal opened onClose={onClose} title={`Budget request for ${club.name}`}
      subtitle="Stored for tracking; there is no online approval"
      submitLabel="Submit request" submitting={submit.isPending} error={submit.error}
      disabled={missing} disabledReason="Fill in every field, including the document link."
      onSubmit={() => submit.mutate({ club_id: club.id, purpose, description,
        amount: Number(amount).toFixed(2), document_url: link },
      { onSuccess: () => { notifyDone("Budget request submitted", club.name); onClose(); } })}>
      <TextInput label="Purpose" required maxLength={200} value={purpose}
        onChange={(e) => setPurpose(e.currentTarget.value)} />
      <NumberInput mt="sm" label="Amount (₹)" required min={0} decimalScale={2} value={amount}
        onChange={setAmount} />
      <Textarea mt="sm" label="Description" required autosize minRows={2} maxLength={4000}
        value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <TextInput mt="sm" label="Supporting document (Google Drive link)" required value={link}
        onChange={(e) => setLink(e.currentTarget.value)} />
    </FormModal>
  );
}

/** UC-GYM-010. */
export function ReportForm({ club, onClose }: FormProps) {
  const submit = useSubmitReport();
  const [incharge, setIncharge] = useState<number | null>(null);
  const [eventName, setEventName] = useState("");
  const [eventAt, setEventAt] = useState("");
  const [description, setDescription] = useState("");
  const [link, setLink] = useState("");
  const missing = incharge === null || !eventName.trim() || !eventAt || !description.trim()
    || !link.trim();
  return (
    <FormModal opened onClose={onClose} title={`Event report for ${club.name}`}
      subtitle="Only the club's leaders and its faculty councillor can read it"
      submitLabel="Submit report" submitting={submit.isPending} error={submit.error}
      disabled={missing} disabledReason="Fill in every field, including the report link."
      onSubmit={() => incharge !== null && submit.mutate({ club_id: club.id,
        student_incharge_user_id: incharge, event_name: eventName,
        event_at: new Date(eventAt).toISOString(), description, report_url: link },
      { onSuccess: () => { notifyDone("Report submitted", club.name); onClose(); } })}>
      <PersonPicker label="Student in charge" kind="student" value={incharge}
        onChange={setIncharge} required />
      <TextInput mt="sm" label="Event name" required maxLength={200} value={eventName}
        onChange={(e) => setEventName(e.currentTarget.value)} />
      <TextInput mt="sm" type="datetime-local" label="Held on" required value={eventAt}
        onChange={(e) => setEventAt(e.currentTarget.value)} />
      <Textarea mt="sm" label="Description" required autosize minRows={2} maxLength={4000}
        value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <TextInput mt="sm" label="Report file (Google Drive link)" required value={link}
        onChange={(e) => setLink(e.currentTarget.value)} />
    </FormModal>
  );
}
