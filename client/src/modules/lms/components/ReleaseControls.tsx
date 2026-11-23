import { Button, Group, Stack, TextInput } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { usePublishMaterial, usePublishAssignment, useWithdrawMaterial, useWithdrawAssignment } from "../api/hooks";
import { Feedback, utcValue } from "./Common";

export function ReleaseControls({ kind, id, state }: {
  kind: "material" | "assignment"; id: number; state: string;
}) {
  const { can } = useAuth();
  const [at, setAt] = useState("");
  const materialPublish = usePublishMaterial(id);
  const assignmentPublish = usePublishAssignment(id);
  const materialWithdraw = useWithdrawMaterial(id);
  const assignmentWithdraw = useWithdrawAssignment(id);
  const publish = kind === "material" ? materialPublish : assignmentPublish;
  const withdraw = kind === "material" ? materialWithdraw : assignmentWithdraw;
  if (!can(`lms.${kind}.publish`) || !["DRAFT", "SCHEDULED"].includes(state)) return null;
  return <Stack>
    <TextInput label="Release at (local time, optional)" type="datetime-local" value={at}
      onChange={(event) => setAt(event.currentTarget.value)} />
    <Group>
      {state === "DRAFT" && <Button loading={(publish.isPending || withdraw.isPending)} onClick={() => publish.mutate(at ? { release_at: utcValue(at) } : {})}>{at ? "Schedule release" : "Publish now"}</Button>}
      {state === "SCHEDULED" && <>
        <Button disabled={!at} loading={(publish.isPending || withdraw.isPending)} onClick={() => publish.mutate({ release_at: utcValue(at) })}>Reschedule release</Button>
        <Button variant="light" loading={(publish.isPending || withdraw.isPending)} onClick={() => withdraw.mutate({})}>Withdraw scheduled content</Button>
      </>}
    </Group><Feedback error={(publish.error || withdraw.error)} success={(publish.isSuccess || withdraw.isSuccess)} />
  </Stack>;
}
