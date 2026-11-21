import { Badge, Group, Paper, Stack, Text } from "@mantine/core";

import type { HistoryMovement } from "../api/types";
import { formatTime } from "../lib/format";

const ACTION_COLOR: Record<string, string> = {
  created: "gray", forwarded: "blue", returned: "orange", archived: "dark",
};

function who(id: string, role: string): string {
  return role ? `${id} (${role})` : id;
}

/** Oldest first, as the server returns it (BR-FTS-008). */
export function HistoryTimeline({ events }: { events: HistoryMovement[] }) {
  if (!events.length) return <Text c="dimmed">No history yet.</Text>;
  return (
    <Stack gap="sm">
      {events.map((m) => (
        <Paper key={m.movement_id} withBorder p="md" radius="md">
          <Group justify="space-between" wrap="wrap" gap="xs">
            <Group gap="xs">
              <Badge color={ACTION_COLOR[m.action] ?? "gray"} variant="light">
                {m.action}
              </Badge>
              <Text size="sm" fw={500}>
                {m.action === "created"
                  ? who(m.from_user_id, m.from_role)
                  : `${who(m.from_user_id, m.from_role)} → ${who(m.to_user_id, m.to_role)}`}
              </Text>
            </Group>
            <Text size="xs" c="dimmed">{formatTime(m.created_at)}</Text>
          </Group>
          {m.comments.map((c, i) => (
            <Text key={i} size="sm" mt="xs">
              {c.remarks}
            </Text>
          ))}
        </Paper>
      ))}
    </Stack>
  );
}

export default HistoryTimeline;
