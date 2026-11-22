import { useState } from "react";
import {
  Button,
  Group,
  Modal,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useReturnFile } from "../api/hooks";
import type { FileListItem } from "../api/types";

interface Props {
  file: FileListItem | null;
  opened: boolean;
  onClose: () => void;
}

export function ReturnModal({ file, opened, onClose }: Props) {
  const [comment, setComment] = useState("");
  const returnMutation = useReturnFile(file?.id ?? 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const trimmed = comment.trim();
    if (!trimmed) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "A return remark/reason is mandatory when returning a file.",
      });
      return;
    }

    returnMutation.mutate(
      { comment: trimmed },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "File Returned",
            message: `File ${file.reference_number} was successfully returned to sender.`,
          });
          setComment("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Return Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Text fw={700}>
          Return File: {file?.reference_number ?? ""}
        </Text>
      }
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Return this file back to the previous sender or file creator with your remarks.
          </Text>

          <Textarea
            label="Return Reason / Remarks (Mandatory)"
            placeholder="Explain why the file is being returned or what modifications are required..."
            value={comment}
            onChange={(e) => setComment(e.currentTarget.value)}
            required
            minRows={3}
            autosize
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={returnMutation.isPending}>
              Cancel
            </Button>
            <Button color="orange" type="submit" loading={returnMutation.isPending}>
              Return File
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
