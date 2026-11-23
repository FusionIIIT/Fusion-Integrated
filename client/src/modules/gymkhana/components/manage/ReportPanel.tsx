import { useState } from "react";
import { Button, FileInput, Stack, Text, Textarea, TextInput } from "@mantine/core";

import { ErrorState } from "../../../../ui/components/ErrorState";
import { useSubmitReport } from "../../api/hooks";
import type { LedClub } from "../../api/types";
import { PersonPicker } from "../PersonPicker";
import { done } from "../toasts";

const BLANK = { event_name: "", event_date: "", description: "" };

export function ReportPanel({ club }: { club: LedClub }) {
  const submit = useSubmitReport();
  const [f, setF] = useState(BLANK);
  const [incharge, setIncharge] = useState<number | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const ready = f.event_name.trim() && f.event_date && incharge !== null && file;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (incharge === null || !file) return;
        submit.mutate({
          club_id: club.id, ...f, event_date: new Date(f.event_date).toISOString(),
          student_incharge_id: incharge, report_file: file,
        }, {
          onSuccess: () => {
            done("Report submitted", "Your Faculty Councillor can now review it.");
            setF(BLANK);
            setIncharge(null);
            setFile(null);
          },
        });
      }}
    >
      <Stack gap="md" maw={560}>
        <Text size="sm" c="dimmed">
          A submitted report is read by the club&apos;s Faculty Councillor.
        </Text>
        {submit.error && <ErrorState error={submit.error} />}
        <TextInput label="Event name" required maxLength={150} value={f.event_name}
          onChange={(e) => setF({ ...f, event_name: e.currentTarget.value })} />
        <TextInput label="Event date and time" type="datetime-local" required value={f.event_date}
          onChange={(e) => setF({ ...f, event_date: e.currentTarget.value })} />
        <PersonPicker label="Student incharge" kind="student" value={incharge}
          onChange={setIncharge} />
        <Textarea label="Description" autosize minRows={3} value={f.description}
          onChange={(e) => setF({ ...f, description: e.currentTarget.value })} />
        <FileInput label="Report file" required clearable value={file} onChange={setFile}
          placeholder="Up to 5 MB" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.txt"
          clearButtonProps={{ "aria-label": "Remove report file" }} />
        <Button type="submit" disabled={!ready} loading={submit.isPending}>Submit report</Button>
      </Stack>
    </form>
  );
}
