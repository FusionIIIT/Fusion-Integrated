import React, { useState } from "react";
import { Alert, Button, Checkbox, Group, Modal, Stack, TextInput, Textarea } from "@mantine/core";
import { getApiErrorMessage, useCreateAnnouncement } from "../api/hooks";

export interface CreateAnnouncementModalProps {
  opened: boolean;
  onClose: () => void;
  courseId: number;
}

export const CreateAnnouncementModal: React.FC<CreateAnnouncementModalProps> = ({
  opened,
  onClose,
  courseId,
}) => {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isPinned, setIsPinned] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const createAnnouncementMutation = useCreateAnnouncement();

  const handleClose = () => {
    setErrorMsg(null);
    setTitle("");
    setContent("");
    setIsPinned(false);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    try {
      await createAnnouncementMutation.mutateAsync({
        course: courseId,
        title,
        content,
        is_pinned: isPinned,
      });
      handleClose();
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={handleClose} title="Publish Course Announcement" size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert color="red" title="Error" withCloseButton onClose={() => setErrorMsg(null)}>
              {errorMsg}
            </Alert>
          )}

          <TextInput
            label="Announcement Title"
            placeholder="e.g. Exam Schedule Update"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
          />

          <Textarea
            label="Content"
            placeholder="Write announcement body..."
            minRows={4}
            value={content}
            onChange={(e) => setContent(e.currentTarget.value)}
            required
          />

          <Checkbox
            label="Pin announcement to top of feed"
            checked={isPinned}
            onChange={(e) => setIsPinned(e.currentTarget.checked)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={createAnnouncementMutation.isPending}>
              Publish Announcement
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default CreateAnnouncementModal;
