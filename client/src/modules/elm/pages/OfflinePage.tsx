import { useState } from "react";
import {
  Button, Container, Group, Select, Stack, TextInput, Textarea,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecordOffline } from "../api/hooks";

const CATEGORIES = ["CL", "RH", "SCL", "EL", "COL", "VL"];

export default function OfflinePage() {
  const record = useRecordOffline();
  const [form, setForm] = useState({
    user_id: "",
    category: "EL",
    start_date: null as Date | null,
    end_date: null as Date | null,
    sanction_reference: "",
    sanction_date: null as Date | null,
    sanctioning_authority: "",
    evidence_description: "",
    reason_elm_unavailable: "",
  });

  function submit() {
    if (!form.start_date || !form.end_date || !form.sanction_date
      || !form.user_id || !form.sanction_reference) {
      notifications.show({ color: "red", title: "Missing fields", message: "Fill every required field." });
      return;
    }
    record.mutate(
      {
        user_id: Number(form.user_id),
        category: form.category,
        start_date: form.start_date.toISOString().slice(0, 10),
        end_date: form.end_date.toISOString().slice(0, 10),
        sanction_reference: form.sanction_reference,
        sanction_date: form.sanction_date.toISOString().slice(0, 10),
        sanctioning_authority: form.sanctioning_authority,
        evidence_description: form.evidence_description,
        reason_elm_unavailable: form.reason_elm_unavailable,
      },
      {
        onSuccess: () => notifications.show({ color: "green", title: "Recorded", message: "The offline leave was posted to the ledger." }),
        onError: (e) => notifications.show({ color: "red", title: "Could not record", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Offline Leave Entry"
        subtitle="Record leave that was sanctioned on paper while ELM was unavailable"
      />
      <Stack maw={640}>
        <Group grow>
          <TextInput
            label="Employee user id" value={form.user_id}
            onChange={(e) => setForm({ ...form, user_id: e.target.value })}
          />
          <Select
            label="Category" data={CATEGORIES} value={form.category}
            onChange={(v) => setForm({ ...form, category: v ?? "EL" })}
          />
        </Group>
        <Group grow>
          <DateInput
            label="From" value={form.start_date}
            onChange={(d) => setForm({ ...form, start_date: d })}
          />
          <DateInput
            label="To" value={form.end_date}
            onChange={(d) => setForm({ ...form, end_date: d })}
          />
        </Group>
        <Group grow>
          <TextInput
            label="Sanction reference" value={form.sanction_reference}
            onChange={(e) => setForm({ ...form, sanction_reference: e.target.value })}
          />
          <DateInput
            label="Sanction date" value={form.sanction_date}
            onChange={(d) => setForm({ ...form, sanction_date: d })}
          />
        </Group>
        <TextInput
          label="Sanctioning authority" value={form.sanctioning_authority}
          onChange={(e) => setForm({ ...form, sanctioning_authority: e.target.value })}
        />
        <Textarea
          label="Evidence description" value={form.evidence_description}
          onChange={(e) => setForm({ ...form, evidence_description: e.target.value })}
        />
        <Textarea
          label="Why ELM was unavailable" value={form.reason_elm_unavailable}
          onChange={(e) => setForm({ ...form, reason_elm_unavailable: e.target.value })}
        />
        <Button loading={record.isPending} onClick={submit}>Record offline leave</Button>
      </Stack>
    </Container>
  );
}
