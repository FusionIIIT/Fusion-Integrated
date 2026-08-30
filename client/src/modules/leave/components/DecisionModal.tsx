import { useState } from "react";
import { Stack, Text, Textarea } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import type { LeaveRequest } from "../api/types";
import { formatDay } from "./PeriodCell";

/** Approve or refuse, with a remark. A refusal requires one: "rejected" with
 *  no stated reason is the complaint this module exists to stop generating. */
export function DecisionModal({
  request, approve, onClose, onConfirm, submitting, error, verb = "Approve",
}: {
  request: LeaveRequest | null;
  approve: boolean;
  onClose: () => void;
  onConfirm: (remark: string) => void;
  submitting?: boolean;
  error?: unknown;
  verb?: string;
}) {
  const [remark, setRemark] = useState("");
  const needsReason = !approve && remark.trim().length === 0;

  return (
    <FormModal
      opened={request != null}
      onClose={() => { setRemark(""); onClose(); }}
      title={approve ? verb : "Refuse"}
      subtitle={request
        ? `${request.category} · ${formatDay(request.starts_on)} to ${formatDay(request.ends_on)}`
        : undefined}
      submitLabel={approve ? verb : "Refuse"}
      danger={!approve}
      disabled={needsReason}
      disabledReason={needsReason ? "A refusal needs a reason." : undefined}
      submitting={submitting}
      error={error}
      onSubmit={() => { onConfirm(remark.trim()); setRemark(""); }}
    >
      <Stack gap="sm">
        {request?.reason && (
          <Text size="sm" c="dimmed">Stated reason: {request.reason}</Text>
        )}
        <Textarea
          label={approve ? "Remark (optional)" : "Reason"}
          placeholder={approve
            ? "Anything the applicant should see alongside the decision"
            : "Why the request cannot be granted"}
          autosize minRows={3}
          value={remark}
          onChange={(e) => setRemark(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
