import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Loader, Modal, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { TbCheck, TbPlayerPlay, TbTrash, TbX } from "react-icons/tb";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecidePurgeRequest, useExecutePurge, usePurgeRequests } from "../api/hooks";
import type { PurgeRequest } from "../api/types";

const STATUS_COLOR: Record<string, string> = {
  pending_it_head: "yellow",
  approved: "green",
  rejected: "red",
  purged: "gray",
  expired: "gray",
};

const COLUMNS: Column<PurgeRequest>[] = [
  { key: "id", header: "ID" },
  { key: "archive_title", header: "Dataset" },
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
    key: "requested_at",
    header: "Requested",
    render: (r) => new Date(r.requested_at).toLocaleDateString(),
  },
  { key: "request_reason", header: "Reason" },
];

export default function PurgePage() {
  const { data, isPending, error } = usePurgeRequests();
  const decide = useDecidePurgeRequest();
  const execute = useExecutePurge();
  const [deciding, setDeciding] = useState<{ req: PurgeRequest; approve: boolean } | null>(null);
  const [executing, setExecuting] = useState<PurgeRequest | null>(null);
  const [comments, setComments] = useState("");

  if (isPending) return <Container size="xl"><Loader mt="xl" /></Container>;
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleDecide() {
    if (!deciding) return;
    decide.mutate(
      { id: deciding.req.id, approve: deciding.approve, comments },
      {
        onSuccess: () => {
          notifications.show({
            color: deciding.approve ? "green" : "orange",
            title: deciding.approve ? "Approved" : "Rejected",
            message: `Purge request #${deciding.req.id} ${deciding.approve ? "approved" : "rejected"}.`,
          });
          setDeciding(null);
          setComments("");
        },
        onError: (e) =>
          notifications.show({ color: "red", title: "Decision failed", message: errorMessage(e) }),
      },
    );
  }

  function handleExecute() {
    if (!executing) return;
    execute.mutate(executing.id, {
      onSuccess: () => {
        notifications.show({
          color: "red",
          title: "Purge executed",
          message: `Dataset permanently purged (request #${executing.id}).`,
        });
        setExecuting(null);
      },
      onError: (e) =>
        notifications.show({ color: "red", title: "Execute failed", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Purge Authorization"
        subtitle="Dual-authorization permanent data destruction requests"
      />

      <Card padding="lg" withBorder>
        <DataTable<PurgeRequest>
          rows={data?.results ?? []}
          loading={isPending}
          columns={[
            ...COLUMNS,
            {
              key: "actions",
              header: "",
              render: (r) => (
                <Group gap="xs">
                  {r.status === "pending_it_head" && (
                    <>
                      <Button
                        size="xs"
                        color="green"
                        variant="light"
                        leftSection={<TbCheck size={11} />}
                        onClick={() => setDeciding({ req: r, approve: true })}
                      >
                        Approve
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        leftSection={<TbX size={11} />}
                        onClick={() => setDeciding({ req: r, approve: false })}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                  {r.status === "approved" && (
                    <Button
                      size="xs"
                      color="red"
                      leftSection={<TbPlayerPlay size={11} />}
                      onClick={() => setExecuting(r)}
                    >
                      Execute Purge
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          rowKey={(r) => r.id}
          empty={{
            icon: TbTrash,
            title: "No purge requests",
            description: "There are currently no purge requests to display.",
          }}
        />
      </Card>

      {/* Decision modal — inline per ADR-0010 */}
      <Modal
        opened={deciding !== null}
        onClose={() => setDeciding(null)}
        title={deciding?.approve ? "Approve Purge Request" : "Reject Purge Request"}
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          <Text size="sm" c="dimmed">Dataset: {deciding?.req.archive_title}</Text>
          <Textarea
            label="Comments"
            placeholder="Provide rationale for decision..."
            value={comments}
            onChange={(e) => setComments(e.currentTarget.value)}
            minRows={3}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeciding(null)}>Cancel</Button>
            <Button
              color={deciding?.approve ? "green" : "red"}
              loading={decide.isPending}
              onClick={handleDecide}
            >
              {deciding?.approve ? "Approve" : "Reject"}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Execute confirmation modal */}
      <Modal
        opened={executing !== null}
        onClose={() => setExecuting(null)}
        title="Confirm Permanent Purge"
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          <Text size="sm" c="red" fw={600}>
            This action is irreversible. All data in this dataset will be permanently destroyed.
          </Text>
          <Text size="sm">Dataset: {executing?.archive_title}</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setExecuting(null)}>Cancel</Button>
            <Button color="red" loading={execute.isPending} onClick={handleExecute}>
              Confirm Permanent Purge
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
