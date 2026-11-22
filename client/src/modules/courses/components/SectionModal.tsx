import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";

import { createSection, updateSection } from "../api/hooks";
import type { CourseMaterialSection } from "../api/types";

interface SectionModalProps {
  opened: boolean;
  onClose: () => void;
  workspaceId: number;
  section?: CourseMaterialSection | null;
  onSuccess: () => void;
}

export function SectionModal({
  opened,
  onClose,
  workspaceId,
  section,
  onSuccess,
}: SectionModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sortOrder, setSortOrder] = useState<number>(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (section) {
      setTitle(section.title);
      setDescription(section.description || "");
      setSortOrder(section.sort_order || 0);
    } else {
      setTitle("");
      setDescription("");
      setSortOrder(0);
    }
    setError(null);
  }, [section, opened]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Section title is required.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (section) {
        await updateSection(workspaceId, section.id, {
          title: title.trim(),
          description: description.trim(),
          sort_order: sortOrder,
        });
      } else {
        await createSection(workspaceId, {
          title: title.trim(),
          description: description.trim(),
          sort_order: sortOrder,
        });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to save section.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={section ? "Edit Module / Section" : "Add Module / Section"}
      size="md"
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {error && (
            <Alert color="red" title="Error">
              {error}
            </Alert>
          )}

          <TextInput
            label="Section Title"
            placeholder="e.g. Module 1: Graph Algorithms"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
            maxLength={120}
          />

          <Textarea
            label="Description (Optional)"
            placeholder="Brief overview of topics covered in this module..."
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            minRows={3}
          />

          <NumberInput
            label="Sort Order"
            value={sortOrder}
            onChange={(v) => setSortOrder(typeof v === "number" ? v : 0)}
            min={0}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              {section ? "Save Changes" : "Create Section"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

