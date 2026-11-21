import { Badge, Group, Paper, Stack, Text, Timeline } from "@mantine/core";
import { FaPaperclip } from "react-icons/fa";

import type { FileMovement } from "../api/types";

const MOVEMENT_COLORS: Record<string, string> = {
  FORWARD: "blue",
  RETURN: "orange",
  ARCHIVE: "teal",
};

export function FileMovementTimeline({ movements }: { movements: FileMovement[] }) {
  if (!movements || movements.length === 0) {
    return <Text size="sm" c="dimmed">No movement records recorded yet.</Text>;
  }

  return (
    <Timeline active={movements.length - 1} bulletSize={18} lineWidth={2}>
      {movements.map((m) => (
        <Timeline.Item
          key={`movement-${m.id}-${m.sequence}`}
          color={MOVEMENT_COLORS[m.movement_type] ?? "gray"}
          title={
            <Group gap="xs" wrap="wrap">
              <Badge size="sm" color={MOVEMENT_COLORS[m.movement_type] ?? "gray"}>
                {m.movement_type} (Step #{m.sequence})
              </Badge>
              <Text size="sm" fw={600}>
                {m.from_username} ({m.from_role || "Employee"}) &rarr; {m.to_username} ({m.to_role || "Employee"})
              </Text>
            </Group>
          }
        >
          <Text size="xs" c="dimmed" mb={4}>
            {new Date(m.created_at).toLocaleString()}
          </Text>

          {m.comments && m.comments.length > 0 && (
            <Stack gap={4} mt={6}>
              {m.comments.map((c) => (
                <Paper key={`c-${c.id}`} p="xs" withBorder bg="var(--mantine-color-gray-0)">
                  <Text size="xs" fw={500} c="dimmed">
                    {c.author_username} ({c.author_role || "Employee"}):
                  </Text>
                  <Text size="sm" mt={2} style={{ whiteSpace: "pre-wrap" }}>
                    {c.comment_text}
                  </Text>
                </Paper>
              ))}
            </Stack>
          )}

          {m.attachments && m.attachments.length > 0 && (
            <Group gap="xs" mt={6}>
              {m.attachments.map((att) => (
                <Badge
                  key={`att-${att.id}`}
                  variant="outline"
                  size="sm"
                  leftSection={<FaPaperclip size={10} />}
                  component="a"
                  href={att.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ cursor: "pointer" }}
                >
                  {att.file_name} ({Math.round(att.file_size / 1024)} KB)
                </Badge>
              ))}
            </Group>
          )}
        </Timeline.Item>
      ))}
    </Timeline>
  );
}
