import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert, Badge, Button, Card, Container, Group, Loader, Stack, Text, Title,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFile, useFileHistory } from "../api/hooks";
import ArchiveModal from "../components/ArchiveModal";
import { FileStatusBadge, PriorityBadge } from "../components/Badges";
import { FtsError } from "../components/FtsError";
import HistoryTimeline from "../components/HistoryTimeline";
import MovementModal from "../components/MovementModal";
import { formatTime } from "../lib/format";
import { actionsFor } from "../lib/rules";

type Dialog = "forward" | "return" | "archive" | null;

/** FTS-UC-005 (open a file) and UC-006 (tracking history), with the actions
 *  UC-003, -004 and -007 available to the current holder. */
export function FileDetailPage() {
  const id = Number(useParams().id);
  const { session } = useAuth();
  const me = session?.user.username;
  const role = session?.active_role || "Employee";

  const file = useFile(id);
  const history = useFileHistory(id);
  const [dialog, setDialog] = useState<Dialog>(null);

  if (file.isPending) return <Container><Loader size="sm" /></Container>;
  if (file.error != null) return <Container><FtsError error={file.error} /></Container>;

  const f = file.data;
  const actions = actionsFor(f, me);
  const events = history.data ?? [];
  const initialComment = events.find((m) => m.action === "created")
    ?.comments[0]?.remarks;

  return (
    <>
      <PageHeader
        title={f.subject}
        subtitle={`File no. ${f.uin}`}
        action={
          <Group gap="xs">
            <FileStatusBadge status={f.status} />
            {actions.readOnly && <Badge color="dark">Read-only</Badge>}
          </Group>
        }
      />

      {actions.readOnly && (
        <Alert color="gray" mb="md">
          This file is archived. It stays readable but cannot be changed or forwarded.
        </Alert>
      )}

      <Card withBorder padding="lg" mb="lg">
        <Stack gap={6}>
          <Group gap="xl">
            <Group gap="xs">
              <Text size="sm">Priority:</Text>
              <PriorityBadge priority={f.priority} />
            </Group>
            <Text size="sm">Category: {f.category}</Text>
          </Group>
          <Text size="sm">
            Created by {f.creator_id}{f.creator_role ? ` (${f.creator_role})` : ""} on {formatTime(f.created_at)}
          </Text>
          <Text size="sm">
            Currently held by {f.current_holder_id}
            {f.current_holder_role ? ` (${f.current_holder_role})` : ""}
          </Text>
          {f.description && <Text size="sm">{f.description}</Text>}
          {initialComment && (
            <Text size="sm" fs="italic">“{initialComment}”</Text>
          )}
        </Stack>

        {(actions.canForward || actions.canReturn || actions.canArchive) && (
          <Group mt="lg">
            {actions.canForward && (
              <Button onClick={() => setDialog("forward")}>
                {f.status === "draft" ? "Send" : "Forward"}
              </Button>
            )}
            {actions.canReturn && (
              <Button variant="default" onClick={() => setDialog("return")}>
                Return
              </Button>
            )}
            {actions.canArchive && (
              <Button color="red" variant="light" onClick={() => setDialog("archive")}>
                Archive
              </Button>
            )}
          </Group>
        )}
      </Card>

      <Title order={3} mb="sm">Tracking history</Title>
      {history.error != null
        ? <FtsError error={history.error} />
        : <HistoryTimeline events={events} />}

      {(dialog === "forward" || dialog === "return") && (
        <MovementModal
          fileId={id} mode={dialog} role={role} onClose={() => setDialog(null)}
        />
      )}
      {dialog === "archive" && (
        <ArchiveModal fileId={id} role={role} onClose={() => setDialog(null)} />
      )}
    </>
  );
}

export default FileDetailPage;
