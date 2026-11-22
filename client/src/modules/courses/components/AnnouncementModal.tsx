import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Modal,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";

import {
  createAnnouncement,
  updateAnnouncement,
} from "../api/hooks";
import type { CourseAnnouncement } from "../api/types";

interface AnnouncementModalProps {
  opened: boolean;
  onClose: () => void;
  workspaceId: number;
  announcement?: CourseAnnouncement | null;
  onSuccess: () => void;
}

export function AnnouncementModal({
  opened,
  onClose,
  workspaceId,
  announcement,
  onSuccess,
}: AnnouncementModalProps) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [isPublished, setIsPublished] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (announcement) {
      setTitle(announcement.title);
      setBody(announcement.body);
      setIsPublished(announcement.is_published);
    } else {
      setTitle("");
      setBody("");
      setIsPublished(true);
    }
    setError(null);
  }, [announcement, opened]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please provide an announcement title.");
      return;
    }
    if (!body.trim()) {
      setError("Please provide an announcement message body.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (announcement) {
        await updateAnnouncement(workspaceId, announcement.id, {
          title: title.trim(),
          body: body.trim(),
          is_published: isPublished,
        });
      } else {
        await createAnnouncement(workspaceId, {
          title: title.trim(),
          body: body.trim(),
          is_published: isPublished,
        });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to save announcement. Please check your inputs.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={announcement ? "Edit Announcement" : "Create Course Announcement"}
      size="lg"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {error && (
            <Alert color="red" title="Error">
              {error}
            </Alert>
          )}

          <TextInput
            label="Announcement Title"
            placeholder="e.g. Midterm Examination Schedule and Syllabus"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
            maxLength={200}
          />

          <Textarea
            label="Message / Body"
            placeholder="Enter announcement details, instructions, or notices here..."
            value={body}
            onChange={(e) => setBody(e.currentTarget.value)}
            required
            minRows={5}
            autosize
          />

          <Checkbox
            label="Publish immediately to all enrolled course members"
            description="If unchecked, this announcement will be saved as a private draft visible only to faculty."
            checked={isPublished}
            onChange={(e) => setIsPublished(e.currentTarget.checked)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              {announcement ? "Save Changes" : "Post Announcement"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

