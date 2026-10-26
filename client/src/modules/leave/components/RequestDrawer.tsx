import {
  Alert, Button, Divider, Drawer, Group, Loader, Stack, Text, Textarea, Timeline,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import {
  useDownloadApplication, useRenominate, useRequest, useRequestCancellation,
  useRequestExtension, useSubmitResumption, useWithdraw,
} from "../api/hooks";
import type { LeaveRequestDetail } from "../api/types";
import { LeaveDate, LeaveStatus, SubstitutePicker, period } from "./fields";

const PENDING = new Set(["awaiting_substitute", "applicant_action_required",
  "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director"]);
const EXTENDABLE = new Set(["EL", "COL", "VL"]);

type Dialog = null | "withdraw" | "cancel" | "extend" | "resume" | "renominate";

/** Every action offered here is one the request's state allows; the server checks again. */
export function RequestDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { session, can } = useAuth();
  const { data: req, isPending, error } = useRequest(id);
  const [dialog, setDialog] = useState<Dialog>(null);
  const download = useDownloadApplication();
  const today = dayjs().format("YYYY-MM-DD");
  const own = req != null && req.user_id === session?.user.id;

  const offers = (r: LeaveRequestDetail) => ({
    withdraw: own && can("leave.request.revoke") && PENDING.has(r.status)
      && r.kind !== "cancellation",
    renominate: own && r.status === "applicant_action_required",
    cancel: own && r.kind === "new" && r.status === "approved" && r.start_date > today,
    extend: own && r.kind === "new" && r.status === "approved" && EXTENDABLE.has(r.category)
      && r.start_date <= today && today <= r.effective_end && !r.resumption,
    resume: own && r.kind === "new" && r.status === "approved" && EXTENDABLE.has(r.category)
      && r.start_date < today && !r.resumption,
  });

  return (
    <Drawer opened={id != null} onClose={onClose} position="right" size="lg"
      title={req ? `${req.category_label} — #${req.id}` : "Leave request"}>
      {isPending && id != null && <Loader size="sm" />}
      {error && <ErrorState error={error} />}
      {req && (
        <Stack gap="md">
          <Group gap="xs">
            <LeaveStatus status={req.status} label={req.status_label} />
            {req.kind !== "new" && <Text size="sm" c="dimmed">{req.kind} of #{req.parent_id}</Text>}
            {req.source === "offline" && <Text size="sm" c="dimmed">recorded offline</Text>}
          </Group>
          <Stack gap={4}>
            <Text size="sm"><b>Period:</b> {period(req)} · {req.days} day(s)</Text>
            {req.effective_end !== req.end_date && (
              <Text size="sm"><b>Extended to:</b> {dayjs(req.effective_end).format("DD MMM YYYY")}</Text>)}
            <Text size="sm"><b>Purpose:</b> {req.purpose || "—"}</Text>
            {req.station_leave && (
              <Text size="sm"><b>Station Leave:</b> {req.station_from} to {req.station_to},
                {" "}{req.station_address}</Text>)}
            {req.unit_head_outcome && (
              <Text size="sm"><b>Unit Head:</b> {req.unit_head_outcome.replace("_", " ")}</Text>)}
            {req.decision && (
              <Text size="sm"><b>Decision:</b> {req.decision} by {req.decided_role}
                {req.decision_remarks ? ` — ${req.decision_remarks}` : ""}</Text>)}
            {req.resumption && (
              <Text size="sm"><b>Resumed:</b> {req.resumption.resumption_date}
                {" "}<LeaveStatus status={req.resumption.status} /></Text>)}
          </Stack>

          {req.status === "applicant_action_required" && (
            <Alert color="orange" variant="light" title="Your substitute declined">
              Nominate another colleague, or withdraw the request.
            </Alert>)}

          <Group gap="xs">
            {offers(req).renominate && <Button size="xs" onClick={() => setDialog("renominate")}>
              Nominate replacement</Button>}
            {offers(req).withdraw && <Button size="xs" color="gray" variant="light"
              onClick={() => setDialog("withdraw")}>Withdraw</Button>}
            {offers(req).cancel && <Button size="xs" variant="light"
              onClick={() => setDialog("cancel")}>Request cancellation</Button>}
            {offers(req).extend && <Button size="xs" variant="light"
              onClick={() => setDialog("extend")}>Request extension</Button>}
            {offers(req).resume && <Button size="xs" variant="light"
              onClick={() => setDialog("resume")}>Submit resumption</Button>}
            {can("leave.request.export") && <Button size="xs" variant="subtle"
              loading={download.isPending}
              onClick={() => download.mutate(req.id, { onError: (e) => notifications.show({
                color: "red", title: "Could not download", message: errorMessage(e) }) })}>
              Download application</Button>}
          </Group>

          <Divider label="History" labelPosition="left" />
          <Timeline bulletSize={14} lineWidth={2}>
            {req.events.map((e) => (
              <Timeline.Item key={e.id} title={e.event.replace(/_/g, " ")}>
                <Text size="xs" c="dimmed">
                  {dayjs(e.at).format("DD MMM YYYY HH:mm")}
                  {e.actor_role ? ` · ${e.actor_role}` : ""}
                </Text>
                {e.remarks && <Text size="sm">{e.remarks}</Text>}
              </Timeline.Item>
            ))}
          </Timeline>
          <ActionDialog dialog={dialog} req={req} onClose={() => setDialog(null)} />
        </Stack>
      )}
    </Drawer>
  );
}

function ActionDialog({ dialog, req, onClose }: {
  dialog: Dialog; req: LeaveRequestDetail; onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const [date, setDate] = useState("");
  const [nominee, setNominee] = useState<number | null>(null);
  const withdraw = useWithdraw();
  const cancel = useRequestCancellation();
  const extend = useRequestExtension();
  const resume = useSubmitResumption();
  const renominate = useRenominate();
  const nextDay = dayjs(req.effective_end).add(1, "day").format("YYYY-MM-DD");

  const run = {
    withdraw: () => withdraw.mutate({ id: req.id, reason }, done("Withdrawn")),
    cancel: () => cancel.mutate({ id: req.id, reason }, done("Cancellation requested")),
    extend: () => extend.mutate({ id: req.id, end_date: date, purpose: reason,
      substitute_user_id: nominee }, done("Extension requested")),
    resume: () => resume.mutate({ id: req.id, resumption_date: date, details: reason },
      done("Resumption submitted")),
    renominate: () => nominee != null && renominate.mutate(
      { id: req.id, substitute_user_id: nominee }, done("Replacement nominated")),
  };
  const pending = withdraw.isPending || cancel.isPending || extend.isPending
    || resume.isPending || renominate.isPending;
  const err = withdraw.error ?? cancel.error ?? extend.error ?? resume.error ?? renominate.error;

  function done(title: string) {
    return { onSuccess: () => { notifications.show({ color: "green", title, message: `#${req.id}` });
      onClose(); } };
  }

  if (!dialog) return null;
  const titles: Record<NonNullable<Dialog>, string> = {
    withdraw: "Withdraw this request", cancel: "Request cancellation",
    extend: "Request an extension", resume: "Submit resumption of duty",
    renominate: "Nominate a replacement substitute",
  };
  const needsDate = dialog === "extend" || dialog === "resume";
  return (
    <FormModal opened onClose={onClose} title={titles[dialog]} submitting={pending} error={err}
      onSubmit={run[dialog]} danger={dialog === "withdraw"}
      disabled={(needsDate && !date) || (dialog === "renominate" && nominee == null)
        || (dialog === "cancel" && !reason.trim())}
      disabledReason={needsDate && !date ? "Choose a date." : "Complete the form."}>
      <Stack>
        {dialog === "extend" && (
          <>
            <Text size="sm">The extension starts {dayjs(nextDay).format("DD MMM YYYY")}, the
              day after your leave currently ends.</Text>
            <LeaveDate label="Extend until" value={date} onChange={setDate} minDate={nextDay} required />
            <SubstitutePicker value={nominee} onChange={setNominee} />
          </>)}
        {dialog === "resume" && (
          <LeaveDate label="Date you returned to duty" value={date} onChange={setDate} required
            description={`Your approved leave ends ${dayjs(req.effective_end).format("DD MMM YYYY")}.`} />)}
        {dialog === "renominate" && (
          <SubstitutePicker value={nominee} onChange={setNominee} required />)}
        {dialog !== "renominate" && (
          <Textarea label={dialog === "resume" ? "Details" : "Reason"} value={reason}
            onChange={(e) => setReason(e.currentTarget.value)} autosize minRows={2}
            required={dialog === "cancel"} />)}
      </Stack>
    </FormModal>
  );
}
