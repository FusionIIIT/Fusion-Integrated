import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Tabs,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaArchive, FaHistory, FaTrash, FaUndo } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useArchivedUsers,
  usePurgeRequests,
  useRestoreUser,
} from "../api/hooks";
import type { ArchivedUserRecord, PurgeRequest } from "../api/types";
import { DualAuthPurgeModal } from "../components/DualAuthPurgeModal";

export default function ArchivalPage() {
  const {
    data: archivedData,
    isPending: archivedPending,
    error: archivedError,
  } = useArchivedUsers();

  const {
    data: purgeData,
    isPending: purgePending,
    error: purgeError,
  } = usePurgeRequests();

  const restoreUser = useRestoreUser();

  const [selectedArchived, setSelectedArchived] =
    useState<ArchivedUserRecord | null>(null);
  const [selectedPurge, setSelectedPurge] = useState<PurgeRequest | null>(null);

  if (archivedError || purgeError) {
    return (
      <Container size="xl">
        <ErrorState error={archivedError || purgeError} />
      </Container>
    );
  }

  const archivedRows = Array.isArray(archivedData)
    ? archivedData
    : Array.isArray((archivedData as any)?.results)
    ? (archivedData as any).results
    : [];

  const purgeRows = Array.isArray(purgeData)
    ? purgeData
    : Array.isArray((purgeData as any)?.results)
    ? (purgeData as any).results
    : [];

  const handleRestore = (record: ArchivedUserRecord) => {
    restoreUser.mutate(
      {
        archive_id: record.basic_user_id,
        reason: "Admin requested account restoration during reversible window",
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Account Restored",
            message: `Account ${record.username} restored to active status.`,
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Restoration Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  const isExpired = (reversibleUntil: string) => {
    return new Date(reversibleUntil).getTime() < Date.now();
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Archival & Purge Lifecycle"
        subtitle="Reversible account retention, recovery, and dual-authorization permanent purge"
      />

      <Tabs defaultValue="archived">
        <Tabs.List mb="md">
          <Tabs.Tab
            value="archived"
            leftSection={<FaArchive size={14} />}
          >
            Archived Accounts ({archivedRows.length})
          </Tabs.Tab>
          <Tabs.Tab
            value="purge"
            leftSection={<FaTrash size={14} />}
          >
            Dual-Auth Purge Queue ({purgeRows.length})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="archived">
          <Card padding="lg" withBorder radius="md">
            <DataTable<ArchivedUserRecord>
              rows={archivedRows}
              loading={archivedPending}
              rowKey={(r) => r.basic_user_id}
              minWidth={900}
              columns={[
                {
                  key: "user",
                  header: "Account",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text fw={600}>{r.username}</Text>
                      <Text size="xs" c="dimmed">
                        {r.email}
                      </Text>
                    </Stack>
                  ),
                },
                {
                  key: "institute_id",
                  header: "Institute ID",
                  render: (r) => <Text size="sm">{r.institute_id}</Text>,
                },
                {
                  key: "archived_at",
                  header: "Archived On",
                  render: (r) => (
                    <Text size="xs">
                      {new Date(r.archived_at).toLocaleDateString()}
                    </Text>
                  ),
                },
                {
                  key: "reversible_until",
                  header: "Reversible Until",
                  render: (r) => {
                    const expired = isExpired(r.reversible_until);
                    return (
                      <Stack gap={0}>
                        <Text size="xs" fw={500} c={expired ? "red" : "blue"}>
                          {new Date(r.reversible_until).toLocaleDateString()}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {expired ? "Window Expired" : "Recovery Open"}
                        </Text>
                      </Stack>
                    );
                  },
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => <StatusBadge status={r.status} />,
                },
                {
                  key: "actions",
                  header: "Actions",
                  align: "right",
                  render: (r) => {
                    const expired = isExpired(r.reversible_until);
                    return (
                      <Group gap="xs" justify="flex-end">
                        <Button
                          size="xs"
                          variant="light"
                          color="teal"
                          disabled={expired || r.status === "restored"}
                          leftSection={<FaUndo size={10} />}
                          onClick={() => handleRestore(r)}
                        >
                          Restore
                        </Button>
                        <Button
                          size="xs"
                          variant="subtle"
                          color="red"
                          leftSection={<FaTrash size={10} />}
                          onClick={() => setSelectedArchived(r)}
                        >
                          Purge
                        </Button>
                      </Group>
                    );
                  },
                },
              ]}
              empty={{
                icon: FaArchive,
                title: "No Archived Accounts",
                description: "No user accounts are currently placed in archival storage.",
              }}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="purge">
          <Card padding="lg" withBorder radius="md">
            <DataTable<PurgeRequest>
              rows={purgeRows}
              loading={purgePending}
              rowKey={(r) => r.id}
              minWidth={900}
              columns={[
                {
                  key: "id",
                  header: "Request ID",
                  render: (r) => (
                    <Text fw={600} size="sm">
                      #{r.id}
                    </Text>
                  ),
                },
                {
                  key: "archive_id",
                  header: "Archive ID",
                  render: (r) => (
                    <Text size="sm">User #{r.archive_id}</Text>
                  ),
                },
                {
                  key: "requested",
                  header: "Requested On",
                  render: (r) => (
                    <Text size="xs">
                      {new Date(r.requested_at).toLocaleString()}
                    </Text>
                  ),
                },
                {
                  key: "reason",
                  header: "Justification",
                  render: (r) => (
                    <Text size="xs" lineClamp={2}>
                      {r.request_reason}
                    </Text>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => <StatusBadge status={r.status} />,
                },
                {
                  key: "actions",
                  header: "Dual-Auth",
                  align: "right",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="red"
                      variant="light"
                      onClick={() => setSelectedPurge(r)}
                    >
                      Review
                    </Button>
                  ),
                },
              ]}
              empty={{
                icon: FaTrash,
                title: "Purge Queue Empty",
                description: "There are no pending dual-authorization purge requests.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      <DualAuthPurgeModal
        archivedUser={selectedArchived}
        purgeRequest={selectedPurge}
        opened={Boolean(selectedArchived || selectedPurge)}
        onClose={() => {
          setSelectedArchived(null);
          setSelectedPurge(null);
        }}
      />
    </Container>
  );
}
