import { useState } from "react";
import {
  Button, Group, Modal, NumberInput, Stack, TextInput, Textarea,
} from "@mantine/core";

import type { CreateLeaveCaseInput, LeaveRequest } from "../types";

export function LeaveCaseForm({
  request, kind, loading, onClose, onSubmit,
}: {
  request: LeaveRequest | null;
  kind: CreateLeaveCaseInput["case_type"] | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (input: CreateLeaveCaseInput) => void;
}) {
  const [reason, setReason] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [resumptionDate, setResumptionDate] = useState("");
  const [substituteId, setSubstituteId] = useState<number | string>("");
  const [evidence, setEvidence] = useState("");
  const title = kind === "cancellation" ? "Cancel approved leave"
    : kind === "extension" ? "Extend leave" : "Submit resumption";

  return (
    <Modal opened={Boolean(request && kind)} onClose={onClose} title={title}>
      <Stack>
        {kind === "extension" && (
          <Group grow>
            <TextInput type="date" label="Extension from" required
              value={start} onChange={(event) => setStart(event.currentTarget.value)} />
            <TextInput type="date" label="Extension to" required
              value={end} onChange={(event) => setEnd(event.currentTarget.value)} />
          </Group>
        )}
        {kind === "extension" && (
          <TextInput label="Medical evidence reference (if required)"
            value={evidence} onChange={(event) => setEvidence(event.currentTarget.value)} />
        )}
        {kind === "resumption" && (
          <TextInput type="date" label="Actual resumption date" required
            value={resumptionDate}
            onChange={(event) => setResumptionDate(event.currentTarget.value)} />
        )}
        {(kind === "extension" || kind === "cancellation") && (
          <NumberInput label="Substitute employee ID (optional)" min={1}
            value={substituteId} onChange={setSubstituteId}
            description="If responsibility coverage is required, the action waits for consent." />
        )}
        <Textarea label="Reason / details" required minRows={3}
          value={reason} onChange={(event) => setReason(event.currentTarget.value)} />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>Close</Button>
          <Button
            loading={loading}
            disabled={!reason.trim()
              || (kind === "extension" && (!start || !end))
              || (kind === "resumption" && !resumptionDate)}
            onClick={() => {
              if (!kind) return;
              onSubmit({
                case_type: kind,
                reason: reason.trim(),
                ...(kind === "extension"
                  ? { requested_start: start, requested_end: end } : {}),
                ...(kind === "resumption"
                  ? { actual_resumption_date: resumptionDate } : {}),
                ...(kind === "extension" && evidence.trim()
                  ? { medical_evidence_ref: evidence.trim() } : {}),
                ...(substituteId && (kind === "extension" || kind === "cancellation")
                  ? { substitute_user_id: Number(substituteId) } : {}),
              });
            }}
          >
            Submit request
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
