import { useState } from "react";
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  TbClock,
  TbDownload,
  TbEdit,
  TbExternalLink,
  TbFileText,
  TbFolder,
  TbLink,
  TbNotes,
  TbPlus,
  TbTrash,
} from "react-icons/tb";

import {
  deleteMaterial,
  deleteSection,
  useCourseMaterials,
  useCourseSections,
} from "../api/hooks";
import type { CourseMaterial, CourseMaterialSection } from "../api/types";
import { MaterialModal } from "./MaterialModal";
import { SectionModal } from "./SectionModal";

interface CourseMaterialsPanelProps {
  workspaceId: number;
  canManage: boolean;
}

export function CourseMaterialsPanel({
  workspaceId,
  canManage,
}: CourseMaterialsPanelProps) {
  const {
    data: sections,
    loading: loadingSections,
    refetch: refetchSections,
  } = useCourseSections(workspaceId);
  const {
    data: materialsData,
    loading: loadingMaterials,
    error: materialsError,
    refetch: refetchMaterials,
  } = useCourseMaterials(workspaceId);

  const [materialModalOpened, setMaterialModalOpened] = useState(false);
  const [sectionModalOpened, setSectionModalOpened] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<CourseMaterial | null>(null);
  const [selectedSection, setSelectedSection] = useState<CourseMaterialSection | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleRefreshAll = () => {
    refetchSections();
    refetchMaterials();
  };

  const handleOpenAddMaterial = () => {
    setSelectedMaterial(null);
    setMaterialModalOpened(true);
  };

  const handleOpenEditMaterial = (m: CourseMaterial) => {
    setSelectedMaterial(m);
    setMaterialModalOpened(true);
  };

  const handleOpenAddSection = () => {
    setSelectedSection(null);
    setSectionModalOpened(true);
  };

  const handleOpenEditSection = (s: CourseMaterialSection) => {
    setSelectedSection(s);
    setSectionModalOpened(true);
  };

  const handleDeleteMaterial = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this material?")) return;
    setActionError(null);
    try {
      await deleteMaterial(workspaceId, id);
      refetchMaterials();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to delete material.");
    }
  };

  const handleDeleteSection = async (id: number) => {
    if (!window.confirm("Delete this section? Any materials in it will become unsectioned.")) return;
    setActionError(null);
    try {
      await deleteSection(workspaceId, id);
      handleRefreshAll();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to delete section.");
    }
  };

  const materials = materialsData?.results ?? [];
  const loading = loadingSections || loadingMaterials;

  const renderMaterialItem = (m: CourseMaterial) => {
    return (
      <Card key={m.id} withBorder shadow="none" p="sm" radius="xs" mb="xs">
        <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
          <Group gap="sm" align="flex-start">
            <div style={{ marginTop: 2 }}>
              {m.material_type === "link" && <TbLink size={20} color="#1971c2" />}
              {m.material_type === "file" && <TbFileText size={20} color="#2b8a3e" />}
              {m.material_type === "note" && <TbNotes size={20} color="#e8590c" />}
            </div>
            <div>
              <Group gap="xs">
                <Text fw={600} size="sm">
                  {m.title}
                </Text>
                <Badge size="xs" variant="outline">
                  {m.material_type.toUpperCase()}
                </Badge>
                {canManage && (
                  <>
                    {m.is_published ? (
                      <Badge size="xs" color="teal">
                        Published
                      </Badge>
                    ) : (
                      <Badge size="xs" color="gray">
                        Draft
                      </Badge>
                    )}
                    {m.is_scheduled && (
                      <Badge size="xs" color="yellow" leftSection={<TbClock size={10} />}>
                        Scheduled
                      </Badge>
                    )}
                  </>
                )}
              </Group>

              {m.description && (
                <Text size="xs" c="dimmed" mt={2}>
                  {m.description}
                </Text>
              )}

              {m.content && (
                <Text
                  size="xs"
                  mt="xs"
                  style={{
                    whiteSpace: "pre-line",
                    background: "#f8f9fa",
                    padding: "8px",
                    borderRadius: "4px",
                  }}
                >
                  {m.content}
                </Text>
              )}

              {m.material_type === "link" && m.link_url && (
                <Button
                  component="a"
                  href={m.link_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="xs"
                  variant="light"
                  leftSection={<TbExternalLink size={14} />}
                  mt="xs"
                >
                  Open External Link
                </Button>
              )}

              {m.material_type === "file" && m.file_url && (
                <Button
                  component="a"
                  href={m.file_url}
                  download
                  size="xs"
                  variant="light"
                  color="teal"
                  leftSection={<TbDownload size={14} />}
                  mt="xs"
                >
                  Download {m.filename || "File"}
                </Button>
              )}
            </div>
          </Group>

          {canManage && (
            <Group gap="xs">
              <Button
                variant="subtle"
                size="xs"
                leftSection={<TbEdit size={13} />}
                onClick={() => handleOpenEditMaterial(m)}
              >
                Edit
              </Button>
              <Button
                variant="subtle"
                color="red"
                size="xs"
                leftSection={<TbTrash size={13} />}
                onClick={() => handleDeleteMaterial(m.id)}
              >
                Delete
              </Button>
            </Group>
          )}
        </Group>
      </Card>
    );
  };

  const unsectionedMaterials = materials.filter((m) => !m.section);

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>Course Learning Materials</Title>
          <Text size="xs" c="dimmed">
            Lecture notes, external links, and reading resources
          </Text>
        </div>
        {canManage && (
          <Group gap="xs">
            <Button
              variant="default"
              size="sm"
              leftSection={<TbFolder size={15} />}
              onClick={handleOpenAddSection}
            >
              Add Section
            </Button>
            <Button
              size="sm"
              leftSection={<TbPlus size={15} />}
              onClick={handleOpenAddMaterial}
            >
              Add Material
            </Button>
          </Group>
        )}
      </Group>

      {materialsError && (
        <Alert color="red" title="Error">
          {materialsError}
        </Alert>
      )}

      {actionError && (
        <Alert color="red" title="Error" withCloseButton onClose={() => setActionError(null)}>
          {actionError}
        </Alert>
      )}

      {loading && (
        <Group justify="center" py="xl">
          <Loader size="md" />
        </Group>
      )}

      {!loading && sections.length === 0 && materials.length === 0 && (
        <Paper withBorder p="xl" ta="center" radius="md">
          <Group justify="center" mb="xs">
            <TbFolder size={32} color="gray" />
          </Group>
          <Text fw={500} c="dimmed">
            No materials uploaded yet
          </Text>
          <Text size="xs" c="dimmed" mt={4}>
            {canManage
              ? "Use the 'Add Section' or 'Add Material' buttons above to structure your course content."
              : "Course materials posted by instructors will appear here."}
          </Text>
        </Paper>
      )}

      {!loading && (sections.length > 0 || materials.length > 0) && (
        <Stack gap="md">
          {/* Sections Accordion */}
          {sections.length > 0 && (
            <Accordion multiple defaultValue={sections.map((s) => String(s.id))}>
              {sections.map((sec) => {
                const secMaterials = materials.filter((m) => m.section === sec.id);
                return (
                  <Accordion.Item key={sec.id} value={String(sec.id)}>
                    <Accordion.Control>
                      <Group justify="space-between" pr="md" wrap="nowrap">
                        <div>
                          <Text fw={600} size="sm">
                            {sec.title}
                          </Text>
                          {sec.description && (
                            <Text size="xs" c="dimmed">
                              {sec.description}
                            </Text>
                          )}
                        </div>
                        <Badge size="xs" variant="light">
                          {secMaterials.length} items
                        </Badge>
                      </Group>
                    </Accordion.Control>
                    <Accordion.Panel>
                      {canManage && (
                        <Group justify="flex-end" gap="xs" mb="xs">
                          <Button
                            variant="subtle"
                            size="xs"
                            leftSection={<TbEdit size={12} />}
                            onClick={() => handleOpenEditSection(sec)}
                          >
                            Edit Section
                          </Button>
                          <Button
                            variant="subtle"
                            color="red"
                            size="xs"
                            leftSection={<TbTrash size={12} />}
                            onClick={() => handleDeleteSection(sec.id)}
                          >
                            Delete Section
                          </Button>
                        </Group>
                      )}
                      {secMaterials.length === 0 ? (
                        <Text size="xs" c="dimmed" fs="italic" py="xs">
                          No materials in this section.
                        </Text>
                      ) : (
                        secMaterials.map((m) => renderMaterialItem(m))
                      )}
                    </Accordion.Panel>
                  </Accordion.Item>
                );
              })}
            </Accordion>
          )}

          {/* Unsectioned Materials */}
          {unsectionedMaterials.length > 0 && (
            <div>
              <Divider
                label="General Materials"
                labelPosition="left"
                my="sm"
              />
              {unsectionedMaterials.map((m) => renderMaterialItem(m))}
            </div>
          )}
        </Stack>
      )}

      <MaterialModal
        opened={materialModalOpened}
        onClose={() => setMaterialModalOpened(false)}
        workspaceId={workspaceId}
        sections={sections}
        material={selectedMaterial}
        onSuccess={refetchMaterials}
      />

      <SectionModal
        opened={sectionModalOpened}
        onClose={() => setSectionModalOpened(false)}
        workspaceId={workspaceId}
        section={selectedSection}
        onSuccess={handleRefreshAll}
      />
    </Stack>
  );
}

