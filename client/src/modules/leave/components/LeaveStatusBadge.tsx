import { Badge } from "@mantine/core";

const COLORS: Record<string, string> = {
  awaiting_substitute: "yellow", applicant_action_required: "orange",
  awaiting_unit_head: "blue", awaiting_establishment: "indigo",
  awaiting_final_decision: "violet", approved: "green", rejected: "red",
  withdrawn: "gray", cancelled: "gray",
};

export function LeaveStatusBadge({ status }: { status: string }) {
  return (
    <Badge color={COLORS[status] ?? "gray"} variant="light" size="sm">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}

export function period(r: { start_date: string; end_date: string; half: string }) {
  const span = r.start_date === r.end_date ? r.start_date : `${r.start_date} → ${r.end_date}`;
  return r.half === "full" ? span : `${span} (${r.half} half)`;
}
