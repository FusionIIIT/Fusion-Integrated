import { useState } from "react";
import { SegmentedControl, SimpleGrid, Stack, Text, TextInput, Textarea } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { useCreateRecord } from "../api/hooks";
import { done } from "./toast";

export function NewRecordModal({ opened, onClose, onCreated }: {
  opened: boolean; onClose: () => void; onCreated: (id: number) => void;
}) {
  const [kind, setKind] = useState<"expense" | "ta">("expense");
  const [form, setForm] = useState<Record<string, string>>({});
  const create = useCreateRecord();
  const set = (k: string) => (e: { currentTarget: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.currentTarget.value }));

  const body = kind === "ta"
    ? { kind, department: form.department ?? "", amount: form.amount || null,
        purpose: form.purpose ?? "", trip_start: form.trip_start || null,
        trip_end: form.trip_end || null,
        documents: form.doc_link ? [{ title: form.doc_title || "Supporting document",
                                      link: form.doc_link }] : [] }
    : { kind, department: form.department ?? "", request_type: form.request_type ?? "",
        title: form.title ?? "", description: form.description ?? "",
        amount: form.amount || null };

  return (
    <FormModal opened={opened} onClose={onClose} error={create.error}
      title={kind === "ta" ? "Submit a TA claim" : "New expense / voucher request"}
      subtitle={kind === "ta" ? "A TA claim goes straight to Finance."
        : "Saved as a draft; attach documents and submit when ready."}
      submitLabel={kind === "ta" ? "Submit claim" : "Save draft"}
      submitting={create.isPending}
      onSubmit={() => create.mutateAsync(body).then((res) => {
        done(kind === "ta" ? "Claim submitted." : "Draft saved.");
        setForm({});
        onCreated(res.data.id);
      }).catch(() => undefined)}>
      <Stack gap="sm" p="lg">
        <SegmentedControl value={kind} onChange={(v) => setKind(v as "expense" | "ta")}
          data={[{ value: "expense", label: "Expense / voucher" },
                 { value: "ta", label: "Travel allowance" }]} />
        <SimpleGrid cols={2}>
          <TextInput label="Department" value={form.department ?? ""}
            onChange={set("department")} />
          <TextInput label="Amount (₹)" value={form.amount ?? ""} onChange={set("amount")}
            inputMode="decimal" />
        </SimpleGrid>
        {kind === "expense" ? (
          <>
            <TextInput label="Request type" description="As listed in the IAA policy"
              value={form.request_type ?? ""} onChange={set("request_type")} />
            <TextInput label="Title" value={form.title ?? ""} onChange={set("title")} />
            <Textarea label="What is it for?" autosize minRows={2}
              value={form.description ?? ""} onChange={set("description")} />
          </>
        ) : (
          <>
            <Textarea label="Purpose of the trip" autosize minRows={2}
              value={form.purpose ?? ""} onChange={set("purpose")} />
            <SimpleGrid cols={2}>
              <TextInput type="date" label="Trip started" value={form.trip_start ?? ""}
                onChange={set("trip_start")} />
              <TextInput type="date" label="Trip ended" value={form.trip_end ?? ""}
                onChange={set("trip_end")} />
            </SimpleGrid>
            <SimpleGrid cols={2}>
              <TextInput label="Document title" value={form.doc_title ?? ""}
                onChange={set("doc_title")} />
              <TextInput label="Document link (https://)" value={form.doc_link ?? ""}
                onChange={set("doc_link")} />
            </SimpleGrid>
            <Text size="xs" c="dimmed">Tickets and bills, as one shared folder link.</Text>
          </>
        )}
      </Stack>
    </FormModal>
  );
}
