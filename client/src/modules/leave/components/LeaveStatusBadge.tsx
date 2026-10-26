import { Badge } from "@mantine/core";

const STATE_COLORS: Record<string, string> = {
  draft: "gray",
  awaiting_substitute: "orange",
  applicant_action_required: "orange",
  awaiting_unit_head: "blue",
  awaiting_establishment: "cyan",
  awaiting_sanction: "indigo",
  awaiting_director: "grape",
  approved: "green",
  rejected: "red",
  withdrawn: "gray",
  cancellation_pending_unit_head: "yellow",
  cancellation_pending_establishment: "yellow",
  cancellation_pending_sanction: "yellow",
  cancelled: "red",
  awaiting_extension_substitute: "orange",
  extension_applicant_action_required: "orange",
  awaiting_extension_unit_head: "grape",
  extension_pending_establishment: "grape",
  extension_pending_sanction: "grape",
  extended: "teal",
  resumption_review_pending: "violet",
  resumption_reviewed_no_adjustment: "teal",
  resumption_reviewed_early_synchronized: "teal",
  resumption_reviewed_late_synchronized: "teal",
};

export function LeaveStatusBadge({ status }: { status: string }) {
  const color = STATE_COLORS[status] ?? "gray";
  const formatted = status.replace(/_/g, " ").toUpperCase();
  return (
    <Badge color={color} variant="light" size="sm">
      {formatted}
    </Badge>
  );
}
