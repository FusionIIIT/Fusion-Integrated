import { Badge, Group, Text, Tooltip } from "@mantine/core";

import type { AcademicStanding } from "../api/types";

/** A CPI always carries the semester it was declared for. */
export function CpiBadge({ cpi, standing, size = "sm" }: {
  cpi: string | null | undefined;
  standing?: AcademicStanding | null;
  size?: "xs" | "sm" | "md";
}) {
  if (cpi == null) {
    return (
      <Tooltip
        label="No declared result yet. Eligibility opens once the result for
               this student's batch is declared."
        multiline w={260} withArrow
      >
        <Badge color="gray" variant="light" size={size}>
          no declared result
        </Badge>
      </Tooltip>
    );
  }

  const sem = standing?.semester;
  const type = (standing?.semester_type ?? "").replace(" Semester", "");
  const provenance = sem ? `Sem ${sem}${type ? ` (${type})` : ""}` : null;

  return (
    <Group gap={6} wrap="nowrap">
      {/* Never shrinks: in a narrow cell an ellipsis would hide the number itself. */}
      <Badge color="teal" variant="light" size={size} style={{ flexShrink: 0 }}>
        CPI {cpi}
      </Badge>
      {provenance && (
        <Tooltip
          label={
            standing?.synced_at
              ? `Declared result, synced ${new Date(standing.synced_at)
                  .toLocaleString()}`
              : "From the last declared result"
          }
          withArrow
        >
          <Text size="xs" c="dimmed" style={{ whiteSpace: "nowrap" }}>
            · {provenance}
          </Text>
        </Tooltip>
      )}
    </Group>
  );
}
