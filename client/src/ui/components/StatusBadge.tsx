import { Badge } from "@mantine/core";

/** One status→colour map, so the same status is never two colours. */
const COLORS: Record<string, string> = {
  draft: "gray",
  submitted: "blue",
  under_review: "indigo",
  shortlisted: "violet",
  offer_issued: "orange",
  offer_accepted: "green",
  offer_declined: "gray",
  rejected: "red",
  withdrawn: "gray",
  published: "green",
  closed: "gray",
  cancelled: "red",
  active: "green",

  // ELM specific statuses
  approved: "green",
  awaiting_substitute: "yellow",
  applicant_action_required: "orange",
  awaiting_unit_head: "blue",
  awaiting_establishment: "cyan",
  awaiting_sanction: "indigo",
  awaiting_director_self_sanction: "violet",
};

export function StatusBadge({ status }: { status: string }) {
  const norm = status.toLowerCase();
  return (
    <Badge color={COLORS[norm] ?? "gray"} variant="light" size="sm">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
