import { Badge } from "@mantine/core";

/** One state to one colour, module-wide. */
const COLORS: Record<string, string> = {
  DRAFT: "gray",
  AWAITING_SUBSTITUTE: "yellow",
  APPLICANT_ACTION_REQUIRED: "orange",
  AWAITING_UNIT_HEAD: "blue",
  AWAITING_ESTABLISHMENT: "indigo",
  AWAITING_FINAL_SANCTION: "violet",
  AWAITING_SELF_SANCTION: "violet",
  APPROVED_NOT_STARTED: "teal",
  ONGOING: "teal",
  AWAITING_RESUMPTION: "cyan",
  AWAITING_RESUMPTION_VERIFICATION: "cyan",
  CLOSED: "green",
  REJECTED: "red",
  WITHDRAWN: "gray",
  CANCELLED: "gray",
  CANCELLATION_UNIT_HEAD: "orange",
  CANCELLATION_ESTABLISHMENT: "orange",
  CANCELLATION_FINAL: "orange",
  EXTENSION_AWAITING_SUBSTITUTE: "yellow",
  EXTENSION_APPLICANT_ACTION_REQUIRED: "orange",
  EXTENSION_AWAITING_UNIT_HEAD: "blue",
  EXTENSION_AWAITING_ESTABLISHMENT: "indigo",
  EXTENSION_AWAITING_FINAL: "violet",
};

export function label(state: string) {
  return state.toLowerCase().replace(/_/g, " ");
}

export function StateBadge({ state }: { state: string }) {
  return (
    <Badge color={COLORS[state] ?? "gray"} variant="light" size="sm">
      {label(state)}
    </Badge>
  );
}
