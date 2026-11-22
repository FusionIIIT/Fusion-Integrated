import { useState } from "react";
import {
  Button,
  Container,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import {
  FaArchive,
  FaEye,
  FaInbox,
  FaPaperPlane,
  FaSearch,
  FaUndo,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useArchiveFile, useInboxFiles } from "../api/hooks";
import type { FileListItem } from "../api/types";
import { FileDetailDrawer } from "../components/FileDetailDrawer";
import { ForwardModal } from "../components/ForwardModal";
import { FtsStatusBadge } from "../components/FtsStatusBadge";
import { ReturnModal } from "../components/ReturnModal";

export default function InboxPage() {
  const { session } = useAuth();
  const currentUserId = session?.user?.id;

  const { data: files, isPending, error } = useInboxFiles();
  const [search, setSearch] = useState("");
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [forwardFile, setForwardFile] = useState<FileListItem | null>(null);
  const [returnFile, setReturnFile] = useState<FileListItem | null>(null);

  const archiveMutation = useArchiveFile();

  const filteredFiles = (files ?? []).filter((f) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      f.reference_number.toLowerCase().includes(q) ||
      f.subject.toLowerCase().includes(q) ||
      f.owner_username.toLowerCase().includes(q)
    );
  });

  const columns: Column<FileListItem>[] = [
    {
      key: "reference_number",
      header: "Reference No.",
      render: (row) => (
        <Text
          size="sm"
          fw={600}
          c="blue"
          style={{ cursor: "pointer" }}
          onClick={() => setSelectedFileId(row.id)}
        >
          {row.reference_number}
        </Text>
      ),
    },
    {
      key: "subject",
      header: "Subject",
      render: (row) => (
        <Text size="sm" lineClamp={2}>
          {row.subject}
        </Text>
      ),
    },
    {
      key: "owner",
      header: "Owner",
      render: (row) => (
        <Text size="sm">
          {row.owner_username} ({row.owner_role || "Employee"})
        </Text>
      ),
    },
    {
      key: "created_at",
      header: "Created",
      render: (row) => (
        <Text size="xs" c="dimmed">
          {new Date(row.created_at).toLocaleDateString()}
        </Text>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <FtsStatusBadge status={row.status} />,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (row) => {
        const isOwner = currentUserId != null && row.owner_user_id === currentUserId;
        return (
          <Group gap="xs" justify="flex-end" wrap="nowrap">
            <Button
              size="xs"
              variant="light"
              leftSection={<FaEye size={12} />}
              onClick={() => setSelectedFileId(row.id)}
            >
              View
            </Button>
            <Button
              size="xs"
              variant="default"
              leftSection={<FaPaperPlane size={12} />}
              onClick={() => setForwardFile(row)}
            >
              Forward
            </Button>
            <Button
              size="xs"
              color="orange"
              variant="subtle"
              leftSection={<FaUndo size={12} />}
              onClick={() => setReturnFile(row)}
            >
              Return
            </Button>
            {isOwner && (
              <Button
                size="xs"
                color="teal"
                variant="subtle"
                leftSection={<FaArchive size={12} />}
                onClick={() => {
                  if (window.confirm(`Archive file ${row.reference_number}?`)) {
                    archiveMutation.mutate(row.id);
                  }
                }}
              >
                Archive
              </Button>
            )}
          </Group>
        );
      },
    },
  ];

  if (error) {
    return (
      <Container size="xl" py="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="File Inbox"
        subtitle="Files currently in your possession awaiting review, action, or onward movement"
      />

      <Stack gap="md">
        <TextInput
          placeholder="Filter by reference number, subject, or owner..."
          leftSection={<FaSearch size={14} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          style={{ maxWidth: 400 }}
        />

        <Paper withBorder>
          <DataTable
            rows={filteredFiles}
            columns={columns}
            loading={isPending}
            rowKey={(r) => r.id}
            empty={{
              icon: FaInbox,
              title: "Inbox is empty",
              description: "You do not currently hold any active files.",
            }}
          />
        </Paper>
      </Stack>

      <FileDetailDrawer
        fileId={selectedFileId}
        onClose={() => setSelectedFileId(null)}
        onForwardClick={(f) => {
          setSelectedFileId(null);
          setForwardFile(f);
        }}
        onReturnClick={(f) => {
          setSelectedFileId(null);
          setReturnFile(f);
        }}
      />

      <ForwardModal
        file={forwardFile}
        opened={forwardFile != null}
        onClose={() => setForwardFile(null)}
      />

      <ReturnModal
        file={returnFile}
        opened={returnFile != null}
        onClose={() => setReturnFile(null)}
      />
    </Container>
  );
}
