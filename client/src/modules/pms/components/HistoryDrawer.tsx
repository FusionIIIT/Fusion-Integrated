import { Badge, Code, Drawer, Group, Stack, Text, Timeline } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { useApplicationHistory } from "../api/hooks";
import { StatusBadge } from "./StatusBadge";

const ROLE_COLORS: Record<string, string> = {
  director: "indigo",
  attorney: "teal",
  pcc_admin: "blue",
  applicant: "orange",
  system: "gray",
};

export function HistoryDrawer({
  applicationId,
  onClose,
}: {
  applicationId: number | null;
  onClose: () => void;
}) {
  const { data, isPending, error } = useApplicationHistory(applicationId ?? undefined);

  return (
    <Drawer
      opened={applicationId != null}
      onClose={onClose}
      position="right"
      size="lg"
      title={<Text fw={700}>Patent Application Audit History</Text>}
    >
      {error && <ErrorState error={error} />}
      {isPending && !error && <Text size="sm" c="dimmed">Loading audit history…</Text>}

      {data && (
        <Stack gap="md">
          {!data.results.length && (
            <Text size="sm" c="dimmed">No audit history recorded yet.</Text>
          )}

          <Timeline active={data.results.length} bulletSize={18} lineWidth={2}>
            {data.results.map((entry) => (
              <Timeline.Item
                key={entry.id}
                color={ROLE_COLORS[entry.actor_role.toLowerCase()] ?? "blue"}
                title={
                  <Group justify="space-between">
                    <Text size="sm" fw={600}>
                      {entry.action_type.replace(/_/g, " ").toUpperCase()}
                    </Text>
                    <Badge size="xs" color={ROLE_COLORS[entry.actor_role.toLowerCase()] ?? "gray"}>
                      {entry.actor_role.toUpperCase()}
                    </Badge>
                  </Group>
                }
              >
                <Stack gap={4} mt={4}>
                  <Text size="xs" c="dimmed">
                    {new Date(entry.created_at).toLocaleString()} (User #{entry.user_id})
                  </Text>
                  {entry.previous_state && entry.new_state && (
                    <Group gap="xs" mt={2}>
                      <StatusBadge status={entry.previous_state} />
                      <Text size="xs">→</Text>
                      <StatusBadge status={entry.new_state} />
                    </Group>
                  )}
                  {entry.details && Object.keys(entry.details).length > 0 && (
                    <Code block mt={4} fz="xs">
                      {JSON.stringify(entry.details, null, 2)}
                    </Code>
                  )}
                </Stack>
              </Timeline.Item>
            ))}
          </Timeline>
        </Stack>
      )}
    </Drawer>
  );
}
