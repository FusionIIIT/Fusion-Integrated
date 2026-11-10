import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Group,
  Modal,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";

import { createMaterial, updateMaterial } from "../api/hooks";
import type { CourseMaterial, CourseMaterialSection } from "../api/types";

interface MaterialModalProps {
  opened: boolean;
  onClose: () => void;
  workspaceId: number;
  sections: CourseMaterialSection[];
  material?: CourseMaterial | null;
  onSuccess: () => void;
}

export function MaterialModal({
  opened,
  onClose,
  workspaceId,
  sections,
  material,
  onSuccess,
}: MaterialModalProps) {
  const [title, setTitle] = useState("");
  const [materialType, setMaterialType] = useState<"note" | "link" | "file">("note");
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [content, setContent] = useState("");
  const [isPublished, setIsPublished] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (material) {
      setTitle(material.title);
      setMaterialType(material.material_type);
      setSectionId(material.section ? String(material.section) : null);
      setDescription(material.description || "");
      setLinkUrl(material.link_url || "");
      setContent(material.content || "");
      setIsPublished(material.is_published);
    } else {
      setTitle("");
      setMaterialType("note");
      setSectionId(null);
      setDescription("");
      setLinkUrl("");
      setContent("");
      setIsPublished(true);
    }
    setError(null);
  }, [material, opened]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Material title is required.");
      return;
    }

    if (materialType === "link" && !linkUrl.trim()) {
      setError("A valid URL is required for link materials.");
      return;
    }

    if (materialType === "note" && !content.trim() && !description.trim()) {
      setError("Content or description is required for notes.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const parsedSectionId = sectionId ? Number(sectionId) : null;
      if (material) {
        await updateMaterial(workspaceId, material.id, {
          title: title.trim(),
          section_id: parsedSectionId,
          clear_section: parsedSectionId === null,
          description: description.trim(),
          link_url: linkUrl.trim(),
          content: content.trim(),
          is_published: isPublished,
        });
      } else {
        await createMaterial(workspaceId, {
          title: title.trim(),
          material_type: materialType,
          section_id: parsedSectionId,
          description: description.trim(),
          link_url: linkUrl.trim(),
          content: content.trim(),
          is_published: isPublished,
        });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to save course material.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const sectionOptions = [
    { value: "", label: "No Section (General)" },
    ...sections.map((s) => ({ value: String(s.id), label: s.title })),
  ];

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={material ? "Edit Course Material" : "Add Course Material"}
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
            label="Title"
            placeholder="e.g. Chapter 1 Lecture Notes"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
            maxLength={200}
          />

          {!material && (
            <Select
              label="Material Type"
              data={[
                { value: "note", label: "Note / Text Content" },
                { value: "link", label: "External Resource Link" },
              ]}
              value={materialType}
              onChange={(v) =>
                setMaterialType((v as "note" | "link" | "file") || "note")
              }
            />
          )}

          <Select
            label="Module / Section"
            placeholder="Select a section"
            data={sectionOptions}
            value={sectionId || ""}
            onChange={(v) => setSectionId(v || null)}
          />

          {materialType === "link" && (
            <TextInput
              label="Resource URL"
              placeholder="https://example.com/resource"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.currentTarget.value)}
              required
            />
          )}

          {materialType === "note" && (
            <Textarea
              label="Content"
              placeholder="Enter note or lecture text..."
              value={content}
              onChange={(e) => setContent(e.currentTarget.value)}
              minRows={4}
              autosize
            />
          )}

          <Textarea
            label="Description (Optional)"
            placeholder="Brief overview of this material..."
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
            minRows={2}
          />

          <Checkbox
            label="Published"
            description="Available to students and TAs immediately"
            checked={isPublished}
            onChange={(e) => setIsPublished(e.currentTarget.checked)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              {material ? "Save Changes" : "Create Material"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

