import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Loader, Modal, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { TbArchive, TbRotateClockwise } from "react-icons/tb";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useArchivedUsers, useRestoreUser } from "../api/hooks";
import type { ArchivedUser } from "../api/types";

const STATUS_COLOR: Record<string, string> = {
  reversible: "blue",
  restored: "green",
  finalized_permanent: "gray",
};

const COLUMNS: Column<ArchivedUser>[] = [
  { key: "username", header: "Username" },
  { key: "institute_id", header: "Institute ID" },
  { key: "user_kind", header: "Kind" },
  {
    key: "status",
    header: "Status",
    render: (r) => (
      <Badge color={STATUS_COLOR[r.status] ?? "gray"} variant="light">
        {r.status.replace("_", " ")}
      </Badge>
    ),
  },
  {
    key: "archived_at",
    header: "Archived",
    render: (r) => new Date(r.archived_at).toLocaleDateString(),
  },
  {
    key: "reversible_until",
    header: "Reversible Until",
    render: (r) => new Date(r.reversible_until).toLocaleDateString(),
  },
];

export default function ArchivalPage() {
  const { data, isPending, error } = useArchivedUsers();
  const restore = useRestoreUser();
  const [restoring, setRestoring] = useState<ArchivedUser | null>(null);
  const [reason, setReason] = useState("");

  if (isPending) return <Container size="xl"><Loader mt="xl" /></Container>;
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleRestore() {
    if (!restoring) return;
    restore.mutate(
      { user_id: restoring.user_id, restoration_reason: reason },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Restored", message: `${restoring.username} restored.` });
          setRestoring(null);
          setReason("");
        },
        onError: (e) =>
          notifications.show({ color: "red", title: "Restore failed", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="Archival Governance" subtitle="Reversible and permanent user archival records" />

      <Card padding="lg" withBorder>
        <DataTable<ArchivedUser>
          rows={data?.results ?? []}
          loading={isPending}
          columns={[
            ...COLUMNS,
            {
              key: "actions",
              header: "",
              render: (r) =>
                r.status === "reversible" ? (
                  <Button
                    size="xs"
                    variant="light"
                    leftSection={<TbRotateClockwise size={11} />}
                    onClick={() => setRestoring(r)}
                  >
                    Restore
                  </Button>
                ) : null,
            },
          ]}
          rowKey={(r) => r.user_id}
          empty={{
            icon: TbArchive,
            title: "No archived users",
            description: "There are currently no users in archival.",
          }}
        />
      </Card>

      {/* Restore drawer — inline per ADR-0010 */}
      <Modal
        opened={restoring !== null}
        onClose={() => setRestoring(null)}
        title={`Restore ${restoring?.username}`}
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          <Text size="sm">
            Reversible until:{" "}
            <strong>{restoring ? new Date(restoring.reversible_until).toLocaleDateString() : ""}</strong>
          </Text>
          <Textarea
            label="Restoration reason"
            placeholder="Rejoining programme..."
            required
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            minRows={3}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRestoring(null)}>Cancel</Button>
            <Button
              color="blue"
              loading={restore.isPending}
              disabled={!reason.trim()}
              onClick={handleRestore}
            >
              Confirm Restore
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
