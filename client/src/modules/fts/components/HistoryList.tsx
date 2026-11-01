import { Badge, Paper, Stack, Text } from "@mantine/core";
import type { HistoryEvent } from "../api/types";

interface HistoryListProps {
  events: HistoryEvent[];
}

function HistoryList({ events }: HistoryListProps) {
  if (events.length === 0) {
    return <Text>No history.</Text>;
  }

  return (
    <Stack gap="md">
      {events.map((event) => (
        <Paper key={event.id} p="md" shadow="sm">
          <Stack>
            <Badge color={event.type === "created" ? "green" : "blue"}>{event.type}</Badge>
            <Text>{event.sender_name} to {event.receiver_name ?? "-"}</Text>
            <Text>{event.created_at.toLocaleString()}</Text>
            {event.comment && <Text>{event.comment}</Text>}
            {event.attachments && event.attachments.length > 0 && (
              <Stack>
                {event.attachments.map((attachment) => (
                  <Text key={attachment.name}>{attachment.name}</Text>
                ))}
              </Stack>
            )}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

export default HistoryList;
