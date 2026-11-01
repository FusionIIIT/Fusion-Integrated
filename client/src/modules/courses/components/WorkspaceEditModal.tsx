import {
  Button,
  Group,
  Modal,
  Stack,
  Switch,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useEffect, useState } from "react";

import { updateWorkspace } from "../api/hooks";
import type { CourseWorkspaceDetail } from "../api/types";

interface Props {
  opened: boolean;
  onClose: () => void;
  workspace: CourseWorkspaceDetail;
  onSaved: () => void;
}

export function WorkspaceEditModal({
  opened,
  onClose,
  workspace,
  onSaved,
}: Props) {
  const [title, setTitle] = useState(workspace.title);
  const [description, setDescription] = useState(workspace.description);
  const [syllabus, setSyllabus] = useState(workspace.syllabus);
  const [schedule, setSchedule] = useState(workspace.schedule);
  const [allowTaAnnouncements, setAllowTaAnnouncements] = useState(
    workspace.allow_ta_announcements,
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTitle(workspace.title);
    setDescription(workspace.description);
    setSyllabus(workspace.syllabus);
    setSchedule(workspace.schedule);
    setAllowTaAnnouncements(workspace.allow_ta_announcements);
  }, [workspace]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateWorkspace(workspace.id, {
        title,
        description,
        syllabus,
        schedule,
        allow_ta_announcements: allowTaAnnouncements,
      });
      onSaved();
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`Configure Workspace: ${workspace.code}`}
      size="lg"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <TextInput
            label="Course Title"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />

          <Textarea
            label="Overview & Description"
            minRows={2}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />

          <Textarea
            label="Course Syllabus"
            description="Detail weekly topics, units, and learning objectives"
            minRows={4}
            value={syllabus}
            onChange={(e) => setSyllabus(e.currentTarget.value)}
          />

          <Textarea
            label="Class & Lab Schedule"
            description="Meeting times, days, and hall or laboratory location"
            minRows={2}
            value={schedule}
            onChange={(e) => setSchedule(e.currentTarget.value)}
          />

          <Switch
            label="Allow Teaching Assistants (TAs) to post announcements"
            description="Permit assigned TAs to post course-wide updates (BR-LMS-007)"
            checked={allowTaAnnouncements}
            onChange={(e) => setAllowTaAnnouncements(e.currentTarget.checked)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={saving}>
              Save Workspace Details
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
