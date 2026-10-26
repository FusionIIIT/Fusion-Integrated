import { Badge } from "@mantine/core";

/** One status→colour map, so the same status is never two colours. */
const COLORS: Record<string, string> = {
  draft: "gray", submitted: "blue", under_review: "indigo",
  shortlisted: "violet", offer_issued: "orange", offer_accepted: "green",
  offer_declined: "gray", rejected: "red", withdrawn: "gray",
  published: "green", closed: "gray", cancelled: "red", active: "green",
  pending_substitute: "yellow", applicant_action_required: "orange",
  pending_unit_head: "blue", pending_authority: "violet",
  approved: "green",
};

export function StatusBadge({ status }: { status: string }) {
  const normalizedStatus = status.toLowerCase();
  return (
    <Badge color={COLORS[status] ?? COLORS[normalizedStatus] ?? "gray"} variant="light" size="sm">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
