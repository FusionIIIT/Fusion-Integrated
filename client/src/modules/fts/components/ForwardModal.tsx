import { useState } from "react";
import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { useForwardFile } from "../api/hooks";
import type { FileListItem } from "../api/types";

const COMMON_ROLES = [
  "Assistant Professor",
  "Associate Professor",
  "Professor",
  "Junior Assistant",
  "Junior Superintendent",
  "Dean Academic",
  "Registrar",
  "Director",
];

interface Props {
  file: FileListItem | null;
  opened: boolean;
  onClose: () => void;
}

export function ForwardModal({ file, opened, onClose }: Props) {
  const [toUserId, setToUserId] = useState<number | string>("");
  const [toUsername, setToUsername] = useState("");
  const [toRole, setToRole] = useState<string | null>("");
  const [comment, setComment] = useState("");

  const forwardMutation = useForwardFile(file?.id ?? 0);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const trimmedComment = comment.trim();
    if (!trimmedComment) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "A movement comment/remark is mandatory when forwarding a file.",
      });
      return;
    }

    const userIdNum = Number(toUserId);
    if (!userIdNum || userIdNum <= 0) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Please enter a valid recipient User ID.",
      });
      return;
    }

    if (!toUsername.trim()) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Please enter recipient username.",
      });
      return;
    }

    if (!toRole?.trim()) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Please specify or select recipient role.",
      });
      return;
    }

    forwardMutation.mutate(
      {
        to_user_id: userIdNum,
        to_username: toUsername.trim(),
        to_role: toRole.trim(),
        comment: trimmedComment,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "File Forwarded",
            message: `File ${file.reference_number} was successfully forwarded to ${toUsername}.`,
          });
          setToUserId("");
          setToUsername("");
          setToRole("");
          setComment("");
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Forward Failed",
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
          Forward File: {file?.reference_number ?? ""}
        </Text>
      }
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Forward this active file to another employee for review, approval, or action.
          </Text>

          <NumberInput
            label="Recipient User ID"
            placeholder="e.g. 42"
            value={toUserId}
            onChange={(val) => setToUserId(val)}
            required
            min={1}
          />

          <TextInput
            label="Recipient Username"
            placeholder="e.g. jdoe"
            value={toUsername}
            onChange={(e) => setToUsername(e.currentTarget.value)}
            required
          />

          <Select
            label="Recipient Role / Designation"
            placeholder="Select role"
            data={COMMON_ROLES}
            value={toRole}
            onChange={setToRole}
            searchable
            nothingFoundMessage="No matching role"
            required
          />

          <Textarea
            label="Remarks / Note (Mandatory)"
            placeholder="Enter reason for forwarding or instructions for the recipient..."
            value={comment}
            onChange={(e) => setComment(e.currentTarget.value)}
            required
            minRows={3}
            autosize
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={forwardMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={forwardMutation.isPending}>
              Forward File
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
