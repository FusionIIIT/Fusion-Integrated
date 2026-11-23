import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Loader, Modal, NumberInput, Select, Stack, Text, TextInput, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { TbArchive, TbDatabaseExport, TbPlus, TbRotateClockwise } from "react-icons/tb";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useArchivedUsers,
  useArchiveUser,
  useCreateHistoricalArchive,
  useHistoricalArchives,
  useRestoreHistoricalArchive,
  useRestoreUser,
} from "../api/hooks";
import type { ArchivedUser, HistoricalArchive } from "../api/types";

const STATUS_COLOR: Record<string, string> = {
  reversible: "blue",
  restored: "green",
  finalized_permanent: "gray",
};

const USER_COLUMNS: Column<ArchivedUser>[] = [
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

const DATASET_COLUMNS: Column<HistoricalArchive>[] = [
  { key: "id", header: "ID" },
  { key: "title", header: "Title" },
  { key: "dataset_category", header: "Category" },
  { key: "record_count", header: "Records" },
  { key: "retention_expires_at", header: "Retention Expires" },
  {
    key: "state",
    header: "State",
    render: (r) => (
      <Badge color={r.is_purged ? "red" : r.is_restored ? "green" : "blue"} variant="light">
        {r.is_purged ? "purged" : r.is_restored ? "restored" : "archived"}
      </Badge>
    ),
  },
];

export default function ArchivalPage() {
  const { data, isPending, error } = useArchivedUsers();
  const { data: datasetData } = useHistoricalArchives();
  const archiveUser = useArchiveUser();
  const restore = useRestoreUser();
  const createDataset = useCreateHistoricalArchive();
  const restoreDataset = useRestoreHistoricalArchive();

  const [restoring, setRestoring] = useState<ArchivedUser | null>(null);
  const [reason, setReason] = useState("");

  const [archiveUserOpen, setArchiveUserOpen] = useState(false);
  const [userId, setUserId] = useState<number | string>(20001);
  const [instituteId, setInstituteId] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [userKind, setUserKind] = useState("student");
  const [archivalReason, setArchivalReason] = useState("");

  const [archiveDatasetOpen, setArchiveDatasetOpen] = useState(false);
  const [datasetCategory, setDatasetCategory] = useState("compliance");
  const [datasetTitle, setDatasetTitle] = useState("");
  const [dateRangeStart, setDateRangeStart] = useState("2018-01-01");
  const [dateRangeEnd, setDateRangeEnd] = useState("2018-12-31");
  const [recordCount, setRecordCount] = useState<number | string>(50);
  const [backupFilePath, setBackupFilePath] = useState("/backups/archive_bundle.tar.gz");
  const [backupChecksum, setBackupChecksum] = useState(
    "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
  );
  const [retentionExpiresAt, setRetentionExpiresAt] = useState("2020-01-01");

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

  function handleArchiveUser() {
    archiveUser.mutate(
      {
        user_id: Number(userId),
        institute_id: instituteId,
        username,
        email,
        user_kind: userKind,
        archival_reason: archivalReason,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Archived", message: `${username} archived.` });
          setArchiveUserOpen(false);
          setInstituteId("");
          setUsername("");
          setEmail("");
          setArchivalReason("");
        },
        onError: (e) =>
          notifications.show({ color: "red", title: "Archival failed", message: errorMessage(e) }),
      },
    );
  }

  function handleCreateDataset() {
    createDataset.mutate(
      {
        dataset_category: datasetCategory,
        title: datasetTitle,
        date_range_start: dateRangeStart,
        date_range_end: dateRangeEnd,
        record_count: Number(recordCount),
        backup_file_path: backupFilePath,
        backup_checksum: backupChecksum,
        retention_expires_at: retentionExpiresAt,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Dataset archived", message: `${datasetTitle} archived.` });
          setArchiveDatasetOpen(false);
          setDatasetTitle("");
        },
        onError: (e) =>
          notifications.show({ color: "red", title: "Dataset archival failed", message: errorMessage(e) }),
      },
    );
  }

  function handleRestoreDataset(archive: HistoricalArchive) {
    restoreDataset.mutate(archive.id, {
      onSuccess: () =>
        notifications.show({ color: "green", title: "Dataset restored", message: `${archive.title} restored.` }),
      onError: (e) =>
        notifications.show({ color: "red", title: "Dataset restore failed", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Archival Governance"
        subtitle="Reversible user archival and historical dataset archives"
        action={
          <Group>
            <Button
              variant="light"
              leftSection={<TbDatabaseExport size={14} />}
              onClick={() => setArchiveDatasetOpen(true)}
            >
              Archive Dataset
            </Button>
            <Button leftSection={<TbPlus size={14} />} onClick={() => setArchiveUserOpen(true)}>
              Archive User
            </Button>
          </Group>
        }
      />

      <Stack gap="lg">
        <Card padding="lg" withBorder>
          <Title order={4} mb="sm">Archived Users</Title>
          <DataTable<ArchivedUser>
            rows={data?.results ?? []}
            loading={isPending}
            columns={[
              ...USER_COLUMNS,
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

        <Card padding="lg" withBorder>
          <Title order={4} mb="sm">Historical Dataset Archives</Title>
          <DataTable<HistoricalArchive>
            rows={datasetData?.results ?? []}
            loading={false}
            columns={[
              ...DATASET_COLUMNS,
              {
                key: "actions",
                header: "",
                render: (r) =>
                  !r.is_purged && !r.is_restored ? (
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<TbRotateClockwise size={11} />}
                      onClick={() => handleRestoreDataset(r)}
                    >
                      Restore Dataset
                    </Button>
                  ) : null,
              },
            ]}
            rowKey={(r) => r.id}
            empty={{
              icon: TbDatabaseExport,
              title: "No historical archives",
              description: "There are currently no historical dataset archives.",
            }}
          />
        </Card>
      </Stack>

      <Modal
        opened={archiveUserOpen}
        onClose={() => setArchiveUserOpen(false)}
        title="Archive Inactive User"
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          <NumberInput label="User ID" required value={userId} onChange={setUserId} min={1} />
          <TextInput
            label="Institute ID"
            placeholder="2021BCS001"
            required
            value={instituteId}
            onChange={(e) => setInstituteId(e.currentTarget.value)}
          />
          <TextInput
            label="Username"
            placeholder="stu001"
            required
            value={username}
            onChange={(e) => setUsername(e.currentTarget.value)}
          />
          <TextInput
            label="Institute Email"
            placeholder="stu001@iiitdmj.ac.in"
            required
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
          />
          <Select
            label="User Kind"
            data={["student", "faculty", "staff"]}
            value={userKind}
            onChange={(v) => setUserKind(v ?? "student")}
          />
          <Textarea
            label="Archival reason"
            placeholder="Graduated / inactive account"
            required
            value={archivalReason}
            onChange={(e) => setArchivalReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setArchiveUserOpen(false)}>Cancel</Button>
            <Button
              loading={archiveUser.isPending}
              disabled={!instituteId.trim() || !username.trim() || !email.trim() || !archivalReason.trim()}
              onClick={handleArchiveUser}
            >
              Confirm Archive User
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={archiveDatasetOpen}
        onClose={() => setArchiveDatasetOpen(false)}
        title="Archive Historical Dataset"
        transitionProps={{ duration: 0 }}
      >
        <Stack>
          <TextInput
            label="Dataset category"
            required
            value={datasetCategory}
            onChange={(e) => setDatasetCategory(e.currentTarget.value)}
          />
          <TextInput
            label="Dataset title"
            placeholder="Compliance Records 2018"
            required
            value={datasetTitle}
            onChange={(e) => setDatasetTitle(e.currentTarget.value)}
          />
          <TextInput
            label="Date range start"
            required
            value={dateRangeStart}
            onChange={(e) => setDateRangeStart(e.currentTarget.value)}
          />
          <TextInput
            label="Date range end"
            required
            value={dateRangeEnd}
            onChange={(e) => setDateRangeEnd(e.currentTarget.value)}
          />
          <NumberInput label="Record count" required value={recordCount} onChange={setRecordCount} min={1} />
          <TextInput
            label="Backup file path"
            required
            value={backupFilePath}
            onChange={(e) => setBackupFilePath(e.currentTarget.value)}
          />
          <TextInput
            label="Backup SHA-256 checksum"
            required
            value={backupChecksum}
            onChange={(e) => setBackupChecksum(e.currentTarget.value)}
          />
          <TextInput
            label="Retention expires at"
            required
            value={retentionExpiresAt}
            onChange={(e) => setRetentionExpiresAt(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setArchiveDatasetOpen(false)}>Cancel</Button>
            <Button
              loading={createDataset.isPending}
              disabled={!datasetTitle.trim() || !backupFilePath.trim() || !backupChecksum.trim()}
              onClick={handleCreateDataset}
            >
              Confirm Archive Dataset
            </Button>
          </Group>
        </Stack>
      </Modal>

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
