import { Badge } from "@mantine/core";

import type { FileStatus } from "../api/types";

const STATUS_COLORS: Record<FileStatus, string> = {
  DRAFT: "yellow",
  CIRCULATED: "blue",
  ARCHIVED: "green",
  DISCARDED: "red",
};

export function FtsStatusBadge({ status }: { status: FileStatus | string }) {
  const norm = (status ?? "DRAFT").toUpperCase() as FileStatus;
  const color = STATUS_COLORS[norm] ?? "gray";

  return (
    <Badge color={color} variant="light" size="sm">
      {norm}
    </Badge>
  );
}
