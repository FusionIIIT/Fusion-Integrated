import { useState } from "react";
import {
  ActionIcon,
  Button,
  Container,
  Group,
  NumberInput,
  Paper,
  Radio,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPaperclip, FaPlus, FaTrash } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateFile } from "../api/hooks";
import type { AttachmentPayload } from "../api/types";

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

export default function CreateFilePage() {
  const navigate = useNavigate();
  const createMutation = useCreateFile();

  const [mode, setMode] = useState<"circulate" | "draft">("circulate");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [comment, setComment] = useState("");

  // Recipient details (if circulating immediately)
  const [recipientUserId, setRecipientUserId] = useState<number | string>("");
  const [recipientUsername, setRecipientUsername] = useState("");
  const [recipientRole, setRecipientRole] = useState<string | null>("");

  // Attachments
  const [attachments, setAttachments] = useState<AttachmentPayload[]>([]);
  const [newAttName, setNewAttName] = useState("");
  const [newAttUrl, setNewAttUrl] = useState("");

  const handleAddAttachment = () => {
    if (!newAttName.trim() || !newAttUrl.trim()) return;
    setAttachments((prev) => [
      ...prev,
      {
        file_name: newAttName.trim(),
        file_url: newAttUrl.trim(),
        file_size: 1024 * 50, // default dummy 50 KB
        mime_type: "application/pdf",
      },
    ]);
    setNewAttName("");
    setNewAttUrl("");
  };

  const handleRemoveAttachment = (idx: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!subject.trim()) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "File subject is required.",
      });
      return;
    }

    if (!comment.trim()) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "An initial file note/comment is mandatory (BR-FTS-006).",
      });
      return;
    }

    const isDraft = mode === "draft";
    let recId: number | null = null;
    let recUsername = "";
    let recRole = "";

    if (!isDraft) {
      recId = Number(recipientUserId);
      if (!recId || recId <= 0) {
        notifications.show({
          color: "red",
          title: "Validation Error",
          message: "Recipient User ID is required when circulating immediately.",
        });
        return;
      }
      if (!recipientUsername.trim()) {
        notifications.show({
          color: "red",
          title: "Validation Error",
          message: "Recipient username is required when circulating immediately.",
        });
        return;
      }
      if (!recipientRole?.trim()) {
        notifications.show({
          color: "red",
          title: "Validation Error",
          message: "Recipient role is required when circulating immediately.",
        });
        return;
      }
      recUsername = recipientUsername.trim();
      recRole = recipientRole.trim();
    }

    createMutation.mutate(
      {
        subject: subject.trim(),
        description: description.trim(),
        comment: comment.trim(),
        is_draft: isDraft,
        recipient_user_id: recId,
        recipient_username: recUsername,
        recipient_role: recRole,
        attachments: attachments.length ? attachments : undefined,
      },
      {
        onSuccess: (file) => {
          notifications.show({
            color: "green",
            title: isDraft ? "Draft Saved" : "File Circulated",
            message: `File ${file.reference_number} created successfully.`,
          });
          navigate(isDraft ? "/fts/drafts" : "/fts/outbox");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Creation Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Container size="md" py="lg">
      <PageHeader
        title="Create Institute File"
        subtitle="Initiate an official tracked file or save as a pre-circulation draft"
      />

      <Paper withBorder p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="lg">
            <Radio.Group
              label="Action Mode"
              description="Choose whether to circulate immediately to a recipient or save as draft"
              value={mode}
              onChange={(val) => setMode(val as "circulate" | "draft")}
            >
              <Group mt="xs">
                <Radio value="circulate" label="Circulate Immediately (Send to Colleague)" />
                <Radio value="draft" label="Save as Draft (Circulate Later)" />
              </Group>
            </Radio.Group>

            <TextInput
              label="Subject"
              description="Clear, concise title representing the file matter"
              placeholder="e.g. Budget Approval Request for Robotics Lab"
              value={subject}
              onChange={(e) => setSubject(e.currentTarget.value)}
              required
              maxLength={255}
            />

            <Textarea
              label="Description (Optional)"
              description="Context, background details, or justification"
              placeholder="Provide any detailed background information regarding this proposal..."
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
              minRows={3}
              autosize
            />

            <Textarea
              label="Initial Note / Remarks (Mandatory)"
              description="Mandatory note explaining the file intent (BR-FTS-006)"
              placeholder="e.g. Submitted for consideration and necessary administrative approval..."
              value={comment}
              onChange={(e) => setComment(e.currentTarget.value)}
              required
              minRows={3}
              autosize
            />

            {mode === "circulate" && (
              <Paper p="md" withBorder bg="var(--mantine-color-gray-0)">
                <Stack gap="sm">
                  <Title order={5}>Recipient Information</Title>
                  <Text size="xs" c="dimmed">
                    Specify the initial officer/faculty member to receive this file.
                  </Text>

                  <NumberInput
                    label="Recipient User ID"
                    placeholder="e.g. 42"
                    value={recipientUserId}
                    onChange={(val) => setRecipientUserId(val)}
                    required
                    min={1}
                  />

                  <TextInput
                    label="Recipient Username"
                    placeholder="e.g. registrar_office"
                    value={recipientUsername}
                    onChange={(e) => setRecipientUsername(e.currentTarget.value)}
                    required
                  />

                  <Select
                    label="Recipient Role / Designation"
                    placeholder="Select or enter role"
                    data={COMMON_ROLES}
                    value={recipientRole}
                    onChange={setRecipientRole}
                    searchable
                    nothingFoundMessage="No matching role"
                    required
                  />
                </Stack>
              </Paper>
            )}

            {/* Attachments Section */}
            <Stack gap="xs">
              <Title order={5}>Attachments (Optional)</Title>
              <Text size="xs" c="dimmed">
                Attach supporting documents (PDF, DOCX, images).
              </Text>

              {attachments.map((att, idx) => (
                <Paper key={`att-${idx}`} p="xs" withBorder>
                  <Group justify="space-between">
                    <Group gap="xs">
                      <FaPaperclip size={14} />
                      <Text size="sm" fw={500}>
                        {att.file_name}
                      </Text>
                      <Text size="xs" c="dimmed">
                        ({att.file_url})
                      </Text>
                    </Group>
                    <ActionIcon color="red" variant="subtle" onClick={() => handleRemoveAttachment(idx)}>
                      <FaTrash size={12} />
                    </ActionIcon>
                  </Group>
                </Paper>
              ))}

              <Group gap="sm" align="flex-end">
                <TextInput
                  placeholder="Document Name (e.g. quote.pdf)"
                  value={newAttName}
                  onChange={(e) => setNewAttName(e.currentTarget.value)}
                  style={{ flex: 1 }}
                />
                <TextInput
                  placeholder="File URL or Platform Link"
                  value={newAttUrl}
                  onChange={(e) => setNewAttUrl(e.currentTarget.value)}
                  style={{ flex: 1 }}
                />
                <Button
                  variant="default"
                  leftSection={<FaPlus size={12} />}
                  onClick={handleAddAttachment}
                  disabled={!newAttName.trim() || !newAttUrl.trim()}
                >
                  Add Attachment
                </Button>
              </Group>
            </Stack>

            <Group justify="flex-end" mt="lg">
              <Button variant="default" onClick={() => navigate(-1)} disabled={createMutation.isPending}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                {mode === "circulate" ? "Circulate File" : "Save as Draft"}
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Container>
  );
}
