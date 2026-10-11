import { Drawer, Group, Loader, Stack, Text, Timeline } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { LeaveStatusBadge } from "./LeaveStatusBadge";
import { useHistory } from "../api/hooks";

/** "Why is my request at this status?" answered without a support request. */
export function HistoryDrawer({ applicationId, onClose }: {
  applicationId: number | null;
  onClose: () => void;
}) {
  const { data, isPending, error } = useHistory(applicationId);

  return (
    <Drawer opened={applicationId !== null} onClose={onClose} position="right"
            title="Request history" size="md">
      {error && <ErrorState error={error} />}
      {isPending && <Loader size="sm" />}
      {data && (
        <Timeline active={data.length - 1} bulletSize={18} lineWidth={2}>
          {data.map((event) => (
            <Timeline.Item key={event.id} title={<LeaveStatusBadge status={event.to_status} />}>
              <Stack gap={2}>
                <Group gap="xs">
                  <Text size="xs" c="dimmed">
                    {new Date(event.at).toLocaleString()}
                  </Text>
                  {event.actor_name && (
                    <Text size="xs" c="dimmed">· {event.actor_name}</Text>
                  )}
                </Group>
                {event.note && <Text size="sm">{event.note}</Text>}
              </Stack>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Drawer>
  );
}
