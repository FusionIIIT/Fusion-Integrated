import { Drawer, Loader, Stack, Text, Timeline } from "@mantine/core";

import { useTrail } from "../api/hooks";
import { label } from "./StateBadge";

/** The whole history of one request. Answers "who has it now, and who has
 *  already seen it" without anyone having to ask the establishment section. */
export function TrailDrawer({ requestId, onClose }: {
  requestId: number | null;
  onClose: () => void;
}) {
  const { data, isPending } = useTrail(requestId);

  return (
    <Drawer
      opened={requestId != null} onClose={onClose} position="right" size="md"
      title="History"
    >
      {isPending && <Loader size="sm" />}
      {data && !data.length && (
        <Text c="dimmed" size="sm">Nothing has happened to this request yet.</Text>
      )}
      {data && data.length > 0 && (
        <Timeline active={data.length - 1} bulletSize={14} lineWidth={2}>
          {data.map((t) => (
            <Timeline.Item key={t.id} title={label(t.to_state)}>
              <Stack gap={2}>
                <Text size="xs" c="dimmed">
                  {t.actor_role.toLowerCase().replace(/_/g, " ")}
                  {" · "}
                  {new Date(t.created_at).toLocaleString()}
                  {t.workflow_ref ? ` · ${t.workflow_ref}` : ""}
                </Text>
                {t.remark && <Text size="sm">{t.remark}</Text>}
              </Stack>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Drawer>
  );
}
