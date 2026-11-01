import { Badge } from "@mantine/core";

const COLORS: Record<string, string> = {
  draft: "gray",
  submitted: "blue",
  assigned_for_review: "cyan",
  under_review: "indigo",
  approved: "teal",
  rejected: "red",
  revisions_requested: "orange",
  assignment_offered: "yellow",
  attorney_assigned: "cyan",
  budget_approved: "lime",
  filed: "blue",
  office_action_received: "orange",
  response_submitted: "indigo",
  hearing_scheduled: "violet",
  appeal_filed: "pink",
  granted: "green",
  renewal_decision_requested: "orange",
  renewal_approved: "teal",
  renewed: "green",
  do_not_renew: "gray",
  abandoned: "dark",
  expired: "dark",
  scheduled: "gray",
  pending: "yellow",
  completed: "green",
};

export function StatusBadge({ status }: { status: string }) {
  const norm = (status || "").toLowerCase();
  return (
    <Badge color={COLORS[norm] ?? "gray"} variant="light" size="sm">
      {status.replace(/_/g, " ").toUpperCase()}
    </Badge>
  );
}
