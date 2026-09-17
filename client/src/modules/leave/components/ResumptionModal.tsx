import { useEffect, useState } from "react";
import { Alert, Stack, Textarea } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useSubmitResumption } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { formatDay } from "./PeriodCell";

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Reporting a return to duty. */
export function ResumptionModal({ request, onClose }: {
  request: LeaveRequest | null;
  onClose: () => void;
}) {
  const submit = useSubmitResumption();
  const [day, setDay] = useState<Date | null>(null);
  const [remark, setRemark] = useState("");

  /** The day after the sanctioned end: a normal return, and the default. */
  const normalReturn = request
    ? new Date(new Date(`${request.ends_on}T00:00:00`).getTime() + 86_400_000)
    : null;

  useEffect(() => {
    if (normalReturn) setDay(normalReturn);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request?.id]);

  const early = Boolean(request && day && iso(day) <= request.ends_on);

  function send() {
    if (!request || !day) return;
    submit.mutateAsync({ id: request.id, resumed_on: iso(day), remark: remark.trim() })
      .then(() => {
        onClose();
        setRemark("");
        notifications.show({
          color: "green", title: "Resumption reported",
          message: "It now awaits verification by the establishment section.",
        });
      })
      .catch((e) => notifications.show({
        color: "red", title: "Not recorded", message: errorMessage(e),
      }));
  }

  return (
    <FormModal
      opened={request != null}
      onClose={onClose}
      title="Report resumption of duty"
      subtitle={request
        ? `Leave sanctioned to ${formatDay(request.ends_on)}`
        : undefined}
      submitLabel="Report"
      submitting={submit.isPending}
      disabled={!day}
      disabledReason={!day ? "Enter the date you resumed." : undefined}
      onSubmit={send}
    >
      <Stack gap="sm">
        <DateInput
          label="First day back at work" value={day} onChange={setDay}
          description={request
            ? `Leave was sanctioned to ${formatDay(request.ends_on)}, so a normal return is the next working day.`
            : undefined}
          minDate={request ? new Date(`${request.starts_on}T00:00:00`) : undefined}
          maxDate={normalReturn ?? undefined}
        />
        {early && (
          <Alert color="teal" variant="light">
            That is before the end of your sanctioned leave. The unused days go
            back to your balance once this is verified.
          </Alert>
        )}
        <Textarea
          label="Remark (optional)" autosize minRows={2}
          value={remark} onChange={(e) => setRemark(e.currentTarget.value)}
        />
      </Stack>
    </FormModal>
  );
}
