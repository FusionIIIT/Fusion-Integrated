import { Button, Group, Stack, TextInput } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useLmsWrite } from "../api/hooks";
import { Feedback, utcValue } from "./Common";

export function ReleaseControls({ kind, id, state }: {
  kind: "material" | "assignment"; id: number; state: string;
}) {
  const { can } = useAuth();
  const [at, setAt] = useState("");
  const write = useLmsWrite();
  if (!can(`lms.${kind}.publish`) || !["DRAFT", "SCHEDULED"].includes(state)) return null;
  const prefix = `/lms/${kind}s/${id}`;
  return <Stack>
    <TextInput label="Release at (local time, optional)" type="datetime-local" value={at}
      onChange={(event) => setAt(event.currentTarget.value)} />
    <Group>
      {state === "DRAFT" && <Button loading={write.isPending} onClick={() => write.mutate({
        path: `${prefix}/publish/`, data: at ? { release_at: utcValue(at) } : {},
      })}>{at ? "Schedule release" : "Publish now"}</Button>}
      {state === "SCHEDULED" && <>
        <Button disabled={!at} loading={write.isPending} onClick={() => write.mutate({
          path: `${prefix}/publish/`, data: { release_at: utcValue(at) },
        })}>Reschedule release</Button>
        <Button variant="light" loading={write.isPending} onClick={() => write.mutate({
          path: `${prefix}/withdraw/`,
        })}>Withdraw scheduled content</Button>
      </>}
    </Group><Feedback error={write.error} success={write.isSuccess} />
  </Stack>;
}
