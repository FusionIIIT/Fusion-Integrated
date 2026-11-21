import { useState } from "react";
import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  Timeline,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheckCircle,
  FaFileAlt,
  FaPaperPlane,
  FaReply,
  FaTrash,
  FaUser,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ftsApi } from "../api";
import type { EmployeeUser, FTSFileDetail } from "../types";

interface Props {
  file: FTSFileDetail | null;
  opened: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

export function FileDetailDrawer({ file, opened, onClose, onRefresh }: Props) {
  const { session } = useAuth();
  const currentUserId = session?.user.id;

  const [forwardModal, setForwardModal] = useState(false);
  const [returnModal, setReturnModal] = useState(false);
  const [archiveModal, setArchiveModal] = useState(false);
  const [remarks, setRemarks] = useState("");
  const [receiverId, setReceiverId] = useState<string | null>(null);
  const [employeeOptions, setEmployeeOptions] = useState<
    Array<{ value: string; label: string }>
  >([]);
  const [submitting, setSubmitting] = useState(false);

  if (!file) return null;

  const isHolder = currentUserId === file.current_holder_id;
  const isOwner = currentUserId === file.owner_id;
  const isCreator = currentUserId === file.creator_id;
  const isCirculating = file.status === "circulating";
  const isDraft = file.status === "draft";

  const handleOpenForward = async () => {
    try {
      const emps = await ftsApi.searchEmployees("");
      setEmployeeOptions(
        emps
          .filter((e) => e.user_id !== currentUserId)
          .map((e: EmployeeUser) => ({
            value: String(e.user_id),
            label: `${e.display_name} (${e.username}) - ${e.department || e.kind}`,
          })),
      );
      setRemarks("");
      setReceiverId(null);
      setForwardModal(true);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleForward = async () => {
    if (!receiverId || !remarks.trim()) {
      notifications.show({
        color: "red",
        message: "Please select a recipient and provide a comment.",
      });
      return;
    }
    setSubmitting(true);
    try {
      await ftsApi.forwardFile(file.file_id, {
        receiver_id: Number(receiverId),
        remarks,
      });
      notifications.show({ color: "green", message: "File forwarded successfully." });
      setForwardModal(false);
      onRefresh();
      onClose();
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReturn = async () => {
    if (!remarks.trim()) {
      notifications.show({ color: "red", message: "Please provide return comments." });
      return;
    }
    setSubmitting(true);
    try {
      await ftsApi.returnFile(file.file_id, { remarks });
      notifications.show({ color: "green", message: "File returned to sender." });
      setReturnModal(false);
      onRefresh();
      onClose();
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchive = async () => {
    setSubmitting(true);
    try {
      await ftsApi.archiveFile(file.file_id, remarks);
      notifications.show({ color: "green", message: "File archived successfully." });
      setArchiveModal(false);
      onRefresh();
      onClose();
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDiscardDraft = async () => {
    if (!confirm("Are you sure you want to discard this draft?")) return;
    try {
      await ftsApi.discardDraft(file.file_id);
      notifications.show({ color: "green", message: "Draft discarded." });
      onRefresh();
      onClose();
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const statusColor: Record<string, string> = {
    draft: "yellow",
    circulating: "blue",
    archived: "green",
    discarded: "gray",
  };

  return (
    <>
      <Drawer
        opened={opened}
        onClose={onClose}
        position="right"
        size="lg"
        title={
          <Group>
            <Text fw={700} size="lg">
              {file.file_id}
            </Text>
            <Badge color={statusColor[file.status] || "gray"}>{file.status}</Badge>
          </Group>
        }
      >
        <Stack gap="md">
          <div>
            <Text size="sm" c="dimmed">
              Subject
            </Text>
            <Text fw={600} size="md">
              {file.subject}
            </Text>
          </div>

          {file.description && (
            <div>
              <Text size="sm" c="dimmed">
                Description
              </Text>
              <Text size="sm">{file.description}</Text>
            </div>
          )}

          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Owner ID
              </Text>
              <Text size="sm" fw={500}>
                {file.owner_id}
              </Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">
                Current Holder ID
              </Text>
              <Text size="sm" fw={500}>
                {file.current_holder_id ?? "None"}
              </Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">
                Created At
              </Text>
              <Text size="sm">{new Date(file.created_at).toLocaleString()}</Text>
            </div>
          </Group>

          <Divider label="Movement History" labelPosition="center" />
          <Timeline active={file.movements.length - 1} bulletSize={24} lineWidth={2}>
            {file.movements.map((m) => (
              <Timeline.Item
                key={m.id}
                bullet={<FaFileAlt size={12} />}
                title={`#${m.sequence_number} ${m.action.toUpperCase()} (${m.sender_id} -> ${m.receiver_id})`}
              >
                <Text size="xs" c="dimmed">
                  {new Date(m.created_at).toLocaleString()}
                </Text>
                {m.remarks && (
                  <Text size="sm" mt={4}>
                    {m.remarks}
                  </Text>
                )}
              </Timeline.Item>
            ))}
          </Timeline>

          <Divider label="Comments" labelPosition="center" />
          <Stack gap="xs">
            {file.comments.map((c) => (
              <Group
                key={c.id}
                p="xs"
                style={{
                  backgroundColor: "var(--mantine-color-gray-0)",
                  borderRadius: 4,
                }}
              >
                <FaUser size={12} />
                <Stack gap={2} style={{ flex: 1 }}>
                  <Group justify="space-between">
                    <Text size="xs" fw={600}>
                      User #{c.author_id} ({c.author_designation || "Employee"})
                    </Text>
                    <Text size="xs" c="dimmed">
                      {new Date(c.created_at).toLocaleString()}
                    </Text>
                  </Group>
                  <Text size="sm">{c.comment_text}</Text>
                </Stack>
              </Group>
            ))}
          </Stack>

          {file.attachments.length > 0 && (
            <>
              <Divider label="Attachments" labelPosition="center" />
              <Stack gap="xs">
                {file.attachments.map((att) => (
                  <Group key={att.id} justify="space-between" p="xs">
                    <Text size="sm">{att.file_name}</Text>
                    <Badge variant="outline" size="xs">
                      {att.file_size} bytes
                    </Badge>
                  </Group>
                ))}
              </Stack>
            </>
          )}

          <Divider my="sm" />
          <Group justify="flex-end">
            {isDraft && isCreator && (
              <Button
                color="red"
                variant="outline"
                leftSection={<FaTrash size={14} />}
                onClick={handleDiscardDraft}
              >
                Discard Draft
              </Button>
            )}

            {isCirculating && isHolder && (
              <>
                <Button
                  color="blue"
                  leftSection={<FaPaperPlane size={14} />}
                  onClick={handleOpenForward}
                >
                  Forward
                </Button>
                {file.movements.length > 0 && (
                  <Button
                    color="orange"
                    variant="outline"
                    leftSection={<FaReply size={14} />}
                    onClick={() => {
                      setRemarks("");
                      setReturnModal(true);
                    }}
                  >
                    Return
                  </Button>
                )}
              </>
            )}

            {isCirculating && isOwner && (
              <Button
                color="green"
                leftSection={<FaCheckCircle size={14} />}
                onClick={() => {
                  setRemarks("");
                  setArchiveModal(true);
                }}
              >
                Archive File
              </Button>
            )}
          </Group>
        </Stack>
      </Drawer>

      <Modal
        opened={forwardModal}
        onClose={() => setForwardModal(false)}
        title="Forward File"
      >
        <Stack>
          <Select
            label="Recipient Employee"
            placeholder="Search and select recipient"
            data={employeeOptions}
            value={receiverId}
            onChange={setReceiverId}
            searchable
            required
          />
          <Textarea
            label="Movement Comment"
            placeholder="Mandatory comment for forward"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setForwardModal(false)}>
              Cancel
            </Button>
            <Button loading={submitting} onClick={handleForward}>
              Send Forward
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={returnModal}
        onClose={() => setReturnModal(false)}
        title="Return File to Previous Sender"
      >
        <Stack>
          <Textarea
            label="Return Comment"
            placeholder="Reason for returning file"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setReturnModal(false)}>
              Cancel
            </Button>
            <Button color="orange" loading={submitting} onClick={handleReturn}>
              Confirm Return
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={archiveModal}
        onClose={() => setArchiveModal(false)}
        title="Archive Completed File"
      >
        <Stack>
          <Text size="sm">
            Archiving permanently closes this file workflow. It will remain readable but
            cannot be forwarded again.
          </Text>
          <TextInput
            label="Archival Remarks (Optional)"
            placeholder="Reason or closing note"
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setArchiveModal(false)}>
              Cancel
            </Button>
            <Button color="green" loading={submitting} onClick={handleArchive}>
              Confirm Archival
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
