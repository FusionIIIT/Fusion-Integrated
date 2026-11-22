import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  FileInput,
  Group,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaExternalLinkAlt,
  FaFileAlt,
  FaFileDownload,
  FaLink,
  FaPlus,
  FaStickyNote,
  FaTrash,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourses, useCreateMaterial, useDeleteMaterial, useMaterials } from "../api/hooks";
import type { CourseMaterial, MaterialType } from "../api/types";

export default function MaterialsPage() {
  const { data: courses } = useCourses();
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const activeId = selectedCourseId ?? courses?.[0]?.course_id ?? null;

  const { data: materials, isPending, error } = useMaterials(activeId);
  const createMaterial = useCreateMaterial();
  const deleteMaterial = useDeleteMaterial();
  const { can } = useAuth();

  const canCreate = can("lms.material.create");
  const canDelete = can("lms.material.delete");

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [materialType, setMaterialType] = useState<MaterialType>("NOTE");
  const [sectionName, setSectionName] = useState("General");
  const [contentText, setContentText] = useState("");
  const [externalUrl, setExternalUrl] = useState("");
  const [fileAttachment, setFileAttachment] = useState<File | null>(null);
  const [releaseDate, setReleaseDate] = useState("");

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const courseOptions = (courses ?? []).map((c) => ({
    value: String(c.course_id),
    label: `${c.course_code}: ${c.title}`,
  }));

  const handleCreate = () => {
    if (!activeId || !title.trim()) return;

    if (materialType === "FILE") {
      const formData = new FormData();
      formData.append("course_id", String(activeId));
      formData.append("title", title);
      formData.append("description", description);
      formData.append("material_type", materialType);
      formData.append("section_name", sectionName || "General");
      if (fileAttachment) formData.append("file_attachment", fileAttachment);
      if (releaseDate) formData.append("release_date", releaseDate);

      createMaterial.mutate(formData, {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Material Created",
            message: "Course material file has been added.",
          });
          setCreating(false);
          resetForm();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Upload Failed",
            message: errorMessage(err),
          });
        },
      });
    } else {
      createMaterial.mutate(
        {
          course_id: activeId,
          title,
          description,
          material_type: materialType,
          section_name: sectionName || "General",
          content_text: contentText,
          external_url: externalUrl,
          release_date: releaseDate || null,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Material Created",
              message: "Course material has been published or scheduled.",
            });
            setCreating(false);
            resetForm();
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Creation Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    }
  };

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setContentText("");
    setExternalUrl("");
    setFileAttachment(null);
    setReleaseDate("");
  };

  const handleDelete = (matId: number) => {
    if (confirm("Are you sure you want to remove this course material?")) {
      deleteMaterial.mutate(matId, {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Deleted",
            message: "Course material has been removed.",
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Delete Failed",
            message: errorMessage(err),
          });
        },
      });
    }
  };

  // Group materials by section
  const sections: Record<string, CourseMaterial[]> = {};
  for (const mat of materials ?? []) {
    const sec = mat.section_name || "General";
    if (!sections[sec]) sections[sec] = [];
    sections[sec].push(mat);
  }

  const getTypeIcon = (type: MaterialType) => {
    switch (type) {
      case "FILE":
        return <FaFileDownload color="var(--mantine-color-blue-6)" />;
      case "LINK":
        return <FaLink color="var(--mantine-color-teal-6)" />;
      case "NOTE":
      default:
        return <FaStickyNote color="var(--mantine-color-orange-6)" />;
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Course Materials"
        subtitle="Access lecture notes, reference links, and reading material"
        action={
          canCreate && activeId ? (
            <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
              Add Material
            </Button>
          ) : undefined
        }
      />

      {courseOptions.length > 0 && (
        <Select
          label="Select Course"
          data={courseOptions}
          value={activeId ? String(activeId) : null}
          onChange={(val) => setSelectedCourseId(val ? Number(val) : null)}
          allowDeselect={false}
          mb="lg"
        />
      )}

      {isPending && <Text c="dimmed">Loading materials…</Text>}

      {!isPending && (!materials || materials.length === 0) && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={8}>
            <FaFileAlt size={28} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No course materials available</Text>
            <Text size="sm" c="dimmed">
              No materials have been released for this course yet.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="xl">
        {Object.entries(sections).map(([secName, items]) => (
          <div key={secName}>
            <Text fw={700} size="lg" mb="xs" c="dimmed">
              {secName}
            </Text>
            <Stack gap="sm">
              {items.map((mat) => (
                <Card key={mat.id} padding="md" withBorder>
                  <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <Group align="flex-start" gap="md">
                      <div style={{ marginTop: 4 }}>{getTypeIcon(mat.material_type)}</div>
                      <Stack gap={4}>
                        <Group gap="xs">
                          <Text fw={600}>{mat.title}</Text>
                          <Badge size="xs" variant="light">
                            {mat.material_type}
                          </Badge>
                          {mat.status !== "PUBLISHED" && (
                            <Badge size="xs" color="yellow">
                              {mat.status}
                            </Badge>
                          )}
                        </Group>
                        {mat.description && (
                          <Text size="sm" c="dimmed">
                            {mat.description}
                          </Text>
                        )}
                        {mat.material_type === "NOTE" && mat.content_text && (
                          <Card padding="xs" bg="var(--mantine-color-gray-0)" mt="xs">
                            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                              {mat.content_text}
                            </Text>
                          </Card>
                        )}
                        {mat.material_type === "LINK" && mat.external_url && (
                          <Button
                            component="a"
                            href={mat.external_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            variant="light"
                            size="xs"
                            rightSection={<FaExternalLinkAlt size={10} />}
                            mt="xs"
                          >
                            Open Link
                          </Button>
                        )}
                        {mat.material_type === "FILE" && mat.file_attachment && (
                          <Button
                            component="a"
                            href={mat.file_attachment}
                            target="_blank"
                            download
                            variant="light"
                            size="xs"
                            leftSection={<FaFileDownload size={10} />}
                            mt="xs"
                          >
                            Download Attachment
                          </Button>
                        )}
                        <Text size="xs" c="dimmed" mt={4}>
                          Added {new Date(mat.created_at).toLocaleDateString()}
                        </Text>
                      </Stack>
                    </Group>
                    {canDelete && (
                      <ActionIcon
                        color="red"
                        variant="subtle"
                        onClick={() => handleDelete(mat.id)}
                      >
                        <FaTrash size={14} />
                      </ActionIcon>
                    )}
                  </Group>
                </Card>
              ))}
            </Stack>
          </div>
        ))}
      </Stack>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Add Course Material"
        subtitle="Publish notes, reference links, or files for students"
        onSubmit={handleCreate}
        submitting={createMaterial.isPending}
        submitLabel="Publish Material"
      >
        <Stack gap="md">
          <TextInput
            label="Title"
            placeholder="e.g. Lecture 1 Slides"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <TextInput
            label="Description"
            placeholder="Optional summary or reading notes"
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <TextInput
            label="Section / Module"
            placeholder="e.g. General, Unit 1, Week 2"
            value={sectionName}
            onChange={(e) => setSectionName(e.currentTarget.value)}
          />
          <Select
            label="Material Type"
            data={[
              { value: "NOTE", label: "Text Note" },
              { value: "LINK", label: "External URL Link" },
              { value: "FILE", label: "File Attachment" },
            ]}
            value={materialType}
            onChange={(v) => setMaterialType((v as MaterialType) || "NOTE")}
            allowDeselect={false}
          />
          {materialType === "NOTE" && (
            <Textarea
              label="Content Text"
              placeholder="Enter note contents here..."
              required
              autosize
              minRows={4}
              value={contentText}
              onChange={(e) => setContentText(e.currentTarget.value)}
            />
          )}
          {materialType === "LINK" && (
            <TextInput
              label="External URL"
              placeholder="https://example.com/slides"
              required
              value={externalUrl}
              onChange={(e) => setExternalUrl(e.currentTarget.value)}
            />
          )}
          {materialType === "FILE" && (
            <FileInput
              label="Upload File"
              placeholder="Select PDF, document, or code file"
              required
              value={fileAttachment}
              onChange={setFileAttachment}
            />
          )}
          <TextInput
            label="Scheduled Release (Optional)"
            placeholder="YYYY-MM-DDTHH:MM (Leave blank for immediate release)"
            value={releaseDate}
            onChange={(e) => setReleaseDate(e.currentTarget.value)}
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
