import { Badge } from "@mantine/core";

import type { ClubStatus as Status } from "../api/types";

const COLOR: Record<Status, string> = { open: "yellow", confirmed: "green" };
const LABEL: Record<Status, string> = { open: "Open", confirmed: "Confirmed" };

export function ClubStatus({ status }: { status: Status }) {
  return <Badge color={COLOR[status]} variant="light">{LABEL[status]}</Badge>;
}
