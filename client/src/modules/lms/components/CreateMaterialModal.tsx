import React, { useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  FileInput,
  Group,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { getApiErrorMessage, useCreateMaterial, useUploadFile } from "../api/hooks";
import type { MaterialType, ModuleSection } from "../api/types";

export interface CreateMaterialModalProps {
  opened: boolean;
  onClose: () => void;
  courseId: number;
  sections: ModuleSection[];
}

export const CreateMaterialModal: React.FC<CreateMaterialModalProps> = ({
  opened,
  onClose,
  courseId,
  sections,
}) => {
  const [title, setTitle] = useState("");
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [materialType, setMaterialType] = useState<MaterialType>("note");
  const [noteContent, setNoteContent] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isPublished, setIsPublished] = useState(true);
  const [scheduledPublishAt, setScheduledPublishAt] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const createMaterialMutation = useCreateMaterial();
  const uploadMutation = useUploadFile();

  const handleClose = () => {
    setErrorMsg(null);
    setTitle("");
    setSectionId(null);
    setMaterialType("note");
    setNoteContent("");
    setLinkUrl("");
    setFile(null);
    setIsPublished(true);
    setScheduledPublishAt("");
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      let fileStorageKey = "";
      if (materialType === "file") {
        if (!file) {
          setErrorMsg("Please select a file to upload.");
          setIsSubmitting(false);
          return;
        }
        const uploadRes = await uploadMutation.mutateAsync(file);
        fileStorageKey = uploadRes.storage_key;
      }

      await createMaterialMutation.mutateAsync({
        course: courseId,
        section: sectionId ? parseInt(sectionId) : null,
        title,
        material_type: materialType,
        note_content: materialType === "note" ? noteContent : undefined,
        link_url: materialType === "link" ? linkUrl : undefined,
        file_storage_key: materialType === "file" ? fileStorageKey : undefined,
        is_published: isPublished,
        scheduled_publish_at: scheduledPublishAt ? new Date(scheduledPublishAt).toISOString() : undefined,
      });

      handleClose();
    } catch (err: unknown) {
      setErrorMsg(getApiErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const sectionOptions = sections.map((s) => ({
    value: String(s.id),
    label: s.title,
  }));

  return (
    <Modal opened={opened} onClose={handleClose} title="Add Course Material" size="lg">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          {errorMsg && (
            <Alert color="red" title="Error" withCloseButton onClose={() => setErrorMsg(null)}>
              {errorMsg}
            </Alert>
          )}

          <TextInput
            label="Material Title"
            placeholder="e.g. Lecture 1 Slides & Reading Notes"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
          />

          <Select
            label="Section / Module"
            placeholder="Choose module (optional)"
            data={sectionOptions}
            value={sectionId}
            onChange={setSectionId}
            clearable
          />

          <SegmentedControl
            value={materialType}
            onChange={(val) => setMaterialType(val as MaterialType)}
            data={[
              { label: "Text Note", value: "note" },
              { label: "File Attachment", value: "file" },
              { label: "External Link", value: "link" },
            ]}
          />

          {materialType === "note" && (
            <Textarea
              label="Note Content"
              placeholder="Lecture notes or reading material..."
              minRows={5}
              value={noteContent}
              onChange={(e) => setNoteContent(e.currentTarget.value)}
              required
            />
          )}

          {materialType === "link" && (
            <TextInput
              label="External Link URL"
              placeholder="https://..."
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.currentTarget.value)}
              required
            />
          )}

          {materialType === "file" && (
            <FileInput
              label="Upload File Document"
              placeholder="Select document"
              value={file}
              onChange={setFile}
              required
            />
          )}

          <Checkbox
            label="Publish Immediately"
            checked={isPublished}
            onChange={(e) => setIsPublished(e.currentTarget.checked)}
          />

          <TextInput
            label="Scheduled Release Date & Time (Optional)"
            placeholder="YYYY-MM-DDTHH:mm:ss"
            type="datetime-local"
            value={scheduledPublishAt}
            onChange={(e) => setScheduledPublishAt(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting}>
              Add Material
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
};

export default CreateMaterialModal;
