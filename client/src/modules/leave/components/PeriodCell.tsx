import { Stack, Text } from "@mantine/core";

import type { LeaveRequest } from "../api/types";

const FMT = new Intl.DateTimeFormat(undefined, {
  day: "2-digit", month: "short", year: "numeric",
});

export function formatDay(iso: string) {
  return FMT.format(new Date(`${iso}T00:00:00`));
}

/** The period and what it costs. */
export function PeriodCell({ request }: { request: LeaveRequest }) {
  const single = request.starts_on === request.ends_on;
  const days = Number(request.actual_days ?? request.requested_days);
  return (
    <Stack gap={0}>
      <Text size="sm">
        {single
          ? formatDay(request.starts_on)
          : `${formatDay(request.starts_on)} — ${formatDay(request.ends_on)}`}
      </Text>
      <Text size="xs" c="dimmed">
        {days} day{days === 1 ? "" : "s"} charged
        {request.half ? ` · ${request.half.toLowerCase()} half` : ""}
      </Text>
    </Stack>
  );
}
