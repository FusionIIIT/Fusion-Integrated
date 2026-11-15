import {
  Button, Card, Container, Drawer, Stack, Text, TextInput, Timeline,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCancel, useExtend, useModify, useMyRequests, usePrint, useRenominate, useRequest,
  useResume, useWithdraw,
} from "../api/hooks";
import type { LeaveInput, LeaveRequest } from "../api/types";
import { EmployeePicker } from "../components/EmployeePicker";
import { LeaveForm, missingReason } from "../components/LeaveForm";
import { LeaveTable } from "../components/LeaveTable";
import { NoteModal } from "../components/NoteModal";

const PENDING = new Set(["awaiting_substitute", "substitute_declined", "awaiting_unit_head",
  "awaiting_establishment", "awaiting_sanction", "awaiting_director"]);
const LONG = new Set(["EL", "COL", "VL"]);
const today = () => new Date().toISOString().slice(0, 10);

type Dialog =
  | { kind: "withdraw" | "cancel"; row: LeaveRequest }
  | { kind: "modify"; row: LeaveRequest; value: LeaveInput }
  | { kind: "renominate"; row: LeaveRequest; sub: number | null }
  | { kind: "extend"; row: LeaveRequest; end: string; purpose: string }
  | { kind: "resume"; row: LeaveRequest; date: string }
  | null;

function toInput(r: LeaveRequest): LeaveInput {
  return { category: r.category, start_date: r.start_date, end_date: r.end_date,
    half: r.half, purpose: r.purpose, medical_evidence: r.medical_evidence,
    station_leave: r.station_leave, station_from: r.station_from, station_to: r.station_to,
    station_address: r.station_address, substitute_user_id: r.substitute_user_id,
    responsibility: r.responsibility };
}

export default function MyLeavePage() {
  const { data, isPending, error } = useMyRequests();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [detail, setDetail] = useState<number | null>(null);
  const history = useRequest(detail);
  const withdraw = useWithdraw();
  const cancel = useCancel();
  const modify = useModify();
  const renominate = useRenominate();
  const extend = useExtend();
  const resume = useResume();
  const print = usePrint();

  const done = (title: string) => ({
    onSuccess: () => { notifications.show({ color: "green", title, message: "" });
      setDialog(null); },
    onError: (e: unknown) => notifications.show({ color: "red", title: "Not done",
      message: errorMessage(e) }),
  });

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function actions(r: LeaveRequest) {
    const out: React.ReactNode[] = [
      <Button key="h" size="xs" variant="subtle" onClick={() => setDetail(r.id)}>History</Button>,
      <Button key="p" size="xs" variant="subtle" onClick={() => print.mutate(r.id)}>Print</Button>,
    ];
    if (PENDING.has(r.status)) {
      if (r.kind === "leave") {
        out.push(<Button key="m" size="xs" variant="light"
          onClick={() => setDialog({ kind: "modify", row: r, value: toInput(r) })}>Modify</Button>);
      }
      out.push(<Button key="w" size="xs" variant="light" color="red"
        onClick={() => setDialog({ kind: "withdraw", row: r })}>Withdraw</Button>);
    }
    if (r.status === "substitute_declined") {
      out.push(<Button key="s" size="xs"
        onClick={() => setDialog({ kind: "renominate", row: r, sub: null })}>
        New substitute</Button>);
    }
    if (r.status === "approved" && r.kind !== "offline") {
      if (r.start_date > today()) {
        out.push(<Button key="c" size="xs" variant="light" color="red"
          onClick={() => setDialog({ kind: "cancel", row: r })}>Cancel</Button>);
      } else if (r.kind === "leave" && LONG.has(r.category)) {
        out.push(<Button key="e" size="xs" variant="light"
          onClick={() => setDialog({ kind: "extend", row: r, end: "", purpose: "" })}>
          Extend</Button>);
        out.push(<Button key="r" size="xs"
          onClick={() => setDialog({ kind: "resume", row: r, date: today() })}>
          Resume duty</Button>);
      }
    }
    return out;
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leave" subtitle="Your applications, extensions and their status" />
      <Card withBorder padding="md">
        <LeaveTable rows={data?.results ?? []} loading={isPending} actions={actions}
          empty={{ title: "No leave applications yet",
            description: "Applications you submit appear here." }} />
      </Card>

      <NoteModal
        opened={dialog?.kind === "withdraw"} title="Withdraw this request?"
        label="Reason (optional)" submitLabel="Withdraw" danger
        submitting={withdraw.isPending} onClose={() => setDialog(null)}
        onSubmit={(reason) => dialog && withdraw.mutate({ id: dialog.row.id, reason },
          done("Request withdrawn"))}
      />
      <NoteModal
        opened={dialog?.kind === "cancel"} title="Request cancellation?"
        subtitle="Cancellation goes through the same approvers as the original leave."
        label="Reason (optional)" submitLabel="Request cancellation" danger
        submitting={cancel.isPending} onClose={() => setDialog(null)}
        onSubmit={(reason) => dialog && cancel.mutate({ id: dialog.row.id, reason },
          done("Cancellation requested"))}
      />
      {dialog?.kind === "modify" && (
        <FormModal opened title="Modify request" onClose={() => setDialog(null)}
          subtitle="Approvals restart once you save."
          submitting={modify.isPending} disabled={!!missingReason(dialog.value)}
          disabledReason={missingReason(dialog.value)}
          onSubmit={() => modify.mutate({ id: dialog.row.id, data: dialog.value },
            done("Request modified"))}>
          <LeaveForm value={dialog.value}
            onChange={(value) => setDialog({ ...dialog, value })} />
        </FormModal>
      )}
      {dialog?.kind === "renominate" && (
        <FormModal opened title="Nominate a new substitute" onClose={() => setDialog(null)}
          submitting={renominate.isPending} disabled={dialog.sub == null}
          onSubmit={() => dialog.sub != null && renominate.mutate(
            { id: dialog.row.id, substitute_user_id: dialog.sub, responsibility: "" },
            done("Substitute nominated"))}>
          <EmployeePicker label="Substitute" value={dialog.sub}
            onChange={(sub) => setDialog({ ...dialog, sub })} />
        </FormModal>
      )}
      {dialog?.kind === "extend" && (
        <FormModal opened title="Extend ongoing leave" onClose={() => setDialog(null)}
          subtitle={`Currently ends ${dialog.row.end_date}`}
          submitting={extend.isPending} disabled={!dialog.end || !dialog.purpose.trim()}
          onSubmit={() => extend.mutate({ id: dialog.row.id, end_date: dialog.end,
            purpose: dialog.purpose, substitute_user_id: null }, done("Extension submitted"))}>
          <Stack>
            <TextInput type="date" label="New end date" value={dialog.end}
              onChange={(e) => setDialog({ ...dialog, end: e.currentTarget.value })} />
            <TextInput label="Reason" value={dialog.purpose}
              onChange={(e) => setDialog({ ...dialog, purpose: e.currentTarget.value })} />
          </Stack>
        </FormModal>
      )}
      {dialog?.kind === "resume" && (
        <FormModal opened title="Submit resumption of duty" onClose={() => setDialog(null)}
          subtitle="Unused days are restored only after your return is verified."
          submitting={resume.isPending} disabled={!dialog.date}
          onSubmit={() => resume.mutate({ id: dialog.row.id, actual_return_date: dialog.date,
            note: "" }, done("Resumption submitted"))}>
          <TextInput type="date" label="Date you resumed duty" value={dialog.date}
            onChange={(e) => setDialog({ ...dialog, date: e.currentTarget.value })} />
        </FormModal>
      )}

      <Drawer opened={detail != null} onClose={() => setDetail(null)} position="right"
        title={`Leave #${detail ?? ""}`}>
        {history.error && <ErrorState error={history.error} />}
        {history.data && (
          <Timeline active={history.data.history.length} bulletSize={14}>
            {history.data.history.map((h, i) => (
              <Timeline.Item key={i} title={h.to_status.replace(/_/g, " ")}>
                <Text size="xs" c="dimmed">
                  {new Date(h.at).toLocaleString()} · {h.event.replace(/_/g, " ")}
                  {h.actor_role ? ` · ${h.actor_role}` : ""}
                </Text>
                {h.note && <Text size="sm">{h.note}</Text>}
              </Timeline.Item>
            ))}
          </Timeline>
        )}
      </Drawer>
    </Container>
  );
}
