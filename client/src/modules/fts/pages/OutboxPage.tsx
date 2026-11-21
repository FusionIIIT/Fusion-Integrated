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
import { FaEye, FaPaperPlane, FaSearch } from "react-icons/fa";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useOutboxFiles } from "../api/hooks";
import type { FileListItem } from "../api/types";
import { FileDetailDrawer } from "../components/FileDetailDrawer";
import { FtsStatusBadge } from "../components/FtsStatusBadge";

export default function OutboxPage() {
  const { data: files, isPending, error } = useOutboxFiles();
  const [search, setSearch] = useState("");
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);

  const filteredFiles = (files ?? []).filter((f) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      f.reference_number.toLowerCase().includes(q) ||
      f.subject.toLowerCase().includes(q) ||
      (f.current_holder_username && f.current_holder_username.toLowerCase().includes(q))
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
      key: "current_holder",
      header: "Current Holder",
      render: (row) => (
        <Text size="sm">
          {row.current_holder_username
            ? `${row.current_holder_username} (${row.current_holder_role || "Employee"})`
            : "—"}
        </Text>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <FtsStatusBadge status={row.status} />,
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
      key: "actions",
      header: "Actions",
      align: "right",
      render: (row) => (
        <Group justify="flex-end">
          <Button
            size="xs"
            variant="light"
            leftSection={<FaEye size={12} />}
            onClick={() => setSelectedFileId(row.id)}
          >
            View History
          </Button>
        </Group>
      ),
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
        title="File Outbox"
        subtitle="Files created or dispatched by you, currently with other departments or officers"
      />

      <Stack gap="md">
        <TextInput
          placeholder="Filter by reference number, subject, or current holder..."
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
              icon: FaPaperPlane,
              title: "Outbox is empty",
              description: "You have not dispatched or forwarded any files yet.",
            }}
          />
        </Paper>
      </Stack>

      <FileDetailDrawer
        fileId={selectedFileId}
        onClose={() => setSelectedFileId(null)}
      />
    </Container>
  );
}
