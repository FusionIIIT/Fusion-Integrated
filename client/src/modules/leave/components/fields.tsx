import { Badge, Loader, Select } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import dayjs from "dayjs";
import { useState } from "react";

import { useEmployeeSearch } from "../api/hooks";

/** A calendar date as the API speaks it, never through toISOString's UTC shift. */
export function iso(d: Date | null): string {
  return d ? dayjs(d).format("YYYY-MM-DD") : "";
}

export function fromIso(s: string | null | undefined): Date | null {
  return s ? dayjs(s, "YYYY-MM-DD").toDate() : null;
}

export function LeaveDate({ label, value, onChange, minDate, required, description }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  minDate?: string;
  required?: boolean;
  description?: string;
}) {
  return (
    <DateInput
      label={label} description={description} required={required} valueFormat="DD MMM YYYY"
      value={fromIso(value)} onChange={(d) => onChange(iso(d))}
      minDate={fromIso(minDate) ?? undefined} clearable={!required}
    />
  );
}

/** Colleagues by name; the server leaves out the person searching. */
export function SubstitutePicker({ value, onChange, required, label = "Substitute" }: {
  value: number | null;
  onChange: (id: number | null) => void;
  required?: boolean;
  label?: string;
}) {
  const [q, setQ] = useState("");
  const { data, isFetching } = useEmployeeSearch(q);
  const options = (data ?? []).map((p) => ({
    value: String(p.user_id),
    label: `${p.display_name} — ${p.department || p.kind}`,
  }));
  return (
    <Select
      label={label} required={required} searchable clearable placeholder="Type a name"
      description="One colleague who will cover your responsibilities"
      data={options} searchValue={q} onSearchChange={setQ}
      value={value != null ? String(value) : null}
      onChange={(v) => onChange(v ? Number(v) : null)}
      rightSection={isFetching ? <Loader size="xs" /> : undefined}
      nothingFoundMessage={q.trim().length < 2 ? "Type at least two letters" : "Nobody found"}
    />
  );
}

const STATUS_COLOR: Record<string, string> = {
  awaiting_substitute: "yellow", applicant_action_required: "orange",
  awaiting_unit_head: "blue", awaiting_establishment: "indigo", awaiting_sanction: "violet",
  awaiting_director: "violet", approved: "green", rejected: "red", withdrawn: "gray",
  cancelled: "gray", review_pending: "blue", reviewed_normal: "green",
  reviewed_early: "teal", reviewed_late: "orange",
};

export function LeaveStatus({ status, label }: { status: string; label?: string }) {
  return (
    <Badge color={STATUS_COLOR[status] ?? "gray"} variant="light" size="sm">
      {label ?? status.replace(/_/g, " ")}
    </Badge>
  );
}

export const STEP_LABELS: Record<string, string> = {
  unit_head: "Unit Head review", establishment: "Establishment routing",
  authority: "Final sanction", director: "Director self-sanction",
  resumption_review: "Resumption review", substitute: "Substitute response",
};

export const ACTION_LABELS: Record<string, string> = {
  approve: "Approve", reject: "Reject", recommend: "Recommend",
  not_recommend: "Not recommended", forward: "Forward", review: "Confirm review",
};

export function period(r: { start_date: string; end_date: string; half?: string }): string {
  const f = (s: string) => dayjs(s).format("DD MMM YYYY");
  const half = r.half ? ` (${r.half} half)` : "";
  return r.start_date === r.end_date ? `${f(r.start_date)}${half}`
    : `${f(r.start_date)} – ${f(r.end_date)}`;
}
