import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaArchive, FaPaperPlane, FaPaperclip, FaUndo } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useArchiveFile, useFileDetail, useFileHistory } from "../api/hooks";
import type { FileListItem } from "../api/types";
import { FileMovementTimeline } from "./FileMovementTimeline";
import { FtsStatusBadge } from "./FtsStatusBadge";

interface Props {
  fileId: number | null;
  onClose: () => void;
  onForwardClick?: (file: FileListItem) => void;
  onReturnClick?: (file: FileListItem) => void;
}

export function FileDetailDrawer({
  fileId,
  onClose,
  onForwardClick,
  onReturnClick,
}: Props) {
  const { session } = useAuth();
  const currentUserId = session?.user?.id;

  const { data: file, isPending: loadingFile, error: fileError } = useFileDetail(fileId);
  const { data: history, isPending: loadingHistory, error: historyError } = useFileHistory(fileId);

  const archiveMutation = useArchiveFile();

  const isOwner = file && currentUserId != null && file.owner_user_id === currentUserId;
  const isHolder = file && currentUserId != null && file.current_holder_user_id === currentUserId;
  const isCirculated = file?.status === "CIRCULATED";

  const handleArchive = () => {
    if (!file) return;
    if (!window.confirm(`Are you sure you want to archive file ${file.reference_number}?`)) {
      return;
    }
    archiveMutation.mutate(file.id, {
      onSuccess: () => {
        notifications.show({
          color: "green",
          title: "File Archived",
          message: `File ${file.reference_number} has been archived.`,
        });
        onClose();
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Archive Failed",
          message: errorMessage(err),
        });
      },
    });
  };

  return (
    <Drawer
      opened={fileId != null}
      onClose={onClose}
      position="right"
      size="xl"
      title={
        <Group gap="xs">
          <Text fw={700} size="lg">
            {file ? file.reference_number : "File Details"}
          </Text>
          {file && <FtsStatusBadge status={file.status} />}
        </Group>
      }
    >
      {fileError && <ErrorState error={fileError} />}
      {loadingFile && (
        <Group justify="center" py="xl">
          <Loader size="md" />
        </Group>
      )}

      {file && (
        <Stack gap="md">
          {/* Action toolbar if user is holder or owner */}
          {isCirculated && (
            <Paper p="sm" withBorder bg="var(--mantine-color-gray-0)">
              <Group justify="space-between" wrap="wrap">
                <Text size="sm" fw={600}>
                  Actions:
                </Text>
                <Group gap="xs">
                  {isHolder && onForwardClick && (
                    <Button
                      size="xs"
                      leftSection={<FaPaperPlane size={12} />}
                      onClick={() => onForwardClick(file)}
                    >
                      Forward
                    </Button>
                  )}
                  {isHolder && onReturnClick && (
                    <Button
                      size="xs"
                      color="orange"
                      variant="light"
                      leftSection={<FaUndo size={12} />}
                      onClick={() => onReturnClick(file)}
                    >
                      Return to Sender
                    </Button>
                  )}
                  {isOwner && (
                    <Button
                      size="xs"
                      color="teal"
                      variant="outline"
                      leftSection={<FaArchive size={12} />}
                      onClick={handleArchive}
                      loading={archiveMutation.isPending}
                    >
                      Archive File
                    </Button>
                  )}
                </Group>
              </Group>
            </Paper>
          )}

          {/* Core Metadata */}
          <Paper p="md" withBorder>
            <Stack gap="xs">
              <Title order={4}>{file.subject}</Title>
              {file.description ? (
                <Text size="sm">{file.description}</Text>
              ) : (
                <Text size="sm" c="dimmed" fs="italic">
                  No detailed description provided.
                </Text>
              )}

              <Divider my="xs" />

              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
                <div>
                  <Text size="xs" c="dimmed">
                    Created By / Owner:
                  </Text>
                  <Text size="sm" fw={500}>
                    {file.owner_username} ({file.owner_role || "Employee"})
                  </Text>
                </div>
                <div>
                  <Text size="xs" c="dimmed">
                    Current Holder:
                  </Text>
                  <Text size="sm" fw={500}>
                    {file.current_holder_username
                      ? `${file.current_holder_username} (${file.current_holder_role || "Employee"})`
                      : "—"}
                  </Text>
                </div>
                <div>
                  <Text size="xs" c="dimmed">
                    Created At:
                  </Text>
                  <Text size="sm">
                    {new Date(file.created_at).toLocaleString()}
                  </Text>
                </div>
                <div>
                  <Text size="xs" c="dimmed">
                    Last Updated:
                  </Text>
                  <Text size="sm">
                    {new Date(file.updated_at).toLocaleString()}
                  </Text>
                </div>
                {file.archived_at && (
                  <div>
                    <Text size="xs" c="dimmed">
                      Archived At:
                    </Text>
                    <Text size="sm" c="teal" fw={500}>
                      {new Date(file.archived_at).toLocaleString()}
                    </Text>
                  </div>
                )}
              </SimpleGrid>
            </Stack>
          </Paper>

          {/* Attachments Section */}
          {file.attachments && file.attachments.length > 0 && (
            <Paper p="md" withBorder>
              <Text fw={600} size="sm" mb="xs">
                File Attachments ({file.attachments.length})
              </Text>
              <Group gap="xs">
                {file.attachments.map((att) => (
                  <Badge
                    key={`file-att-${att.id}`}
                    variant="outline"
                    leftSection={<FaPaperclip size={10} />}
                    component="a"
                    href={att.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ cursor: "pointer" }}
                  >
                    {att.file_name} ({Math.round(att.file_size / 1024)} KB)
                  </Badge>
                ))}
              </Group>
            </Paper>
          )}

          {/* Movement History Section */}
          <Paper p="md" withBorder>
            <Title order={5} mb="sm">
              Movement History & Lifecycle Trail
            </Title>
            {loadingHistory && <Loader size="sm" />}
            {historyError && <ErrorState error={historyError} />}
            {history && <FileMovementTimeline movements={history} />}
          </Paper>
        </Stack>
      )}
    </Drawer>
  );
}
