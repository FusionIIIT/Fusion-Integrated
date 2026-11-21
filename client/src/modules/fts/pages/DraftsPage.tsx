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
import { notifications } from "@mantine/notifications";
import { FaFileAlt, FaPaperPlane, FaPlus, FaSearch, FaTrash } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDiscardDraft, useDraftFiles } from "../api/hooks";
import type { FileListItem } from "../api/types";
import { ForwardModal } from "../components/ForwardModal";
import { FtsStatusBadge } from "../components/FtsStatusBadge";

export default function DraftsPage() {
  const navigate = useNavigate();
  const { data: files, isPending, error } = useDraftFiles();
  const [search, setSearch] = useState("");
  const [circulateFile, setCirculateFile] = useState<FileListItem | null>(null);

  const discardMutation = useDiscardDraft();

  const filteredFiles = (files ?? []).filter((f) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      f.reference_number.toLowerCase().includes(q) ||
      f.subject.toLowerCase().includes(q)
    );
  });

  const handleDiscard = (file: FileListItem) => {
    if (!window.confirm(`Are you sure you want to discard draft "${file.reference_number}"? This action cannot be undone.`)) {
      return;
    }

    discardMutation.mutate(file.id, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "Draft Discarded",
          message: `Draft ${file.reference_number} was permanently discarded.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Discard Failed",
          message: errorMessage(err),
        });
      },
    });
  };

  const columns: Column<FileListItem>[] = [
    {
      key: "reference_number",
      header: "Reference No.",
      render: (row) => (
        <Text size="sm" fw={600}>
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
        <Group justify="flex-end" gap="xs">
          <Button
            size="xs"
            variant="default"
            leftSection={<FaPaperPlane size={12} />}
            onClick={() => setCirculateFile(row)}
          >
            Circulate
          </Button>
          <Button
            size="xs"
            color="red"
            variant="subtle"
            leftSection={<FaTrash size={12} />}
            onClick={() => handleDiscard(row)}
          >
            Discard
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
        title="Draft Files"
        subtitle="Uncirculated file notes prepared by you"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => navigate("/fts/create")}>
            New File
          </Button>
        }
      />

      <Stack gap="md">
        <TextInput
          placeholder="Filter drafts by reference number or subject..."
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
              icon: FaFileAlt,
              title: "No drafts found",
              description: "You have no uncirculated file drafts.",
            }}
          />
        </Paper>
      </Stack>

      <ForwardModal
        file={circulateFile}
        opened={circulateFile != null}
        onClose={() => setCirculateFile(null)}
      />
    </Container>
  );
}
