import React, { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Center,
  Divider,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourseMaterials, useCourseSections } from "../api/hooks";
import { CreateMaterialModal } from "../components/CreateMaterialModal";
import { CreateSectionModal } from "../components/CreateSectionModal";
import { MaterialItem } from "../components/MaterialItem";

export interface MaterialsPageProps {
  courseId?: number;
}

export const MaterialsPage: React.FC<MaterialsPageProps> = ({ courseId: propCourseId }) => {
  const { courseId: paramCourseId } = useParams<{ courseId: string }>();
  const courseId = propCourseId ?? (paramCourseId ? parseInt(paramCourseId) : 0);

  const [sectionModalOpened, setSectionModalOpened] = useState(false);
  const [materialModalOpened, setMaterialModalOpened] = useState(false);

  const {
    data: sections,
    isLoading: sectionsLoading,
    error: sectionsError,
  } = useCourseSections(courseId);

  const {
    data: materials,
    isLoading: materialsLoading,
    error: materialsError,
  } = useCourseMaterials(courseId);

  const isLoading = sectionsLoading || materialsLoading;
  const isError = sectionsError || materialsError;

  return (
    <Stack gap="lg">
      <PageHeader
        title="Course Materials & Modules"
        subtitle="Lecture notes, documents, and reference resources"
        action={
          <Group gap="xs">
            <Button variant="default" size="sm" onClick={() => setSectionModalOpened(true)}>
              Add Section
            </Button>
            <Button variant="filled" size="sm" onClick={() => setMaterialModalOpened(true)}>
              Add Material
            </Button>
          </Group>
        }
      />

      {isLoading && (
        <Center py="xl">
          <Loader size="lg" />
        </Center>
      )}

      {isError && (
        <Alert color="red" title="Error Loading Materials">
          Unable to retrieve course sections or materials.
        </Alert>
      )}

      {!isLoading && sections && (
        <Stack gap="xl">
          {sections.map((section) => {
            const sectionMaterials = (materials || []).filter(
              (m) => m.section === section.id
            );

            return (
              <Paper key={section.id} withBorder p="md" radius="md">
                <Group justify="space-between" align="baseline" mb="xs">
                  <Title order={3} size="h4">
                    {section.title}
                  </Title>
                  <Text size="xs" c="dimmed">
                    Order: {section.order}
                  </Text>
                </Group>

                {section.description && (
                  <Text size="sm" c="dimmed" mb="md">
                    {section.description}
                  </Text>
                )}

                <Divider my="sm" />

                {sectionMaterials.length > 0 ? (
                  <Stack gap="xs">
                    {sectionMaterials.map((m) => (
                      <MaterialItem key={m.id} material={m} />
                    ))}
                  </Stack>
                ) : (
                  <Text size="sm" c="dimmed" fs="italic">
                    No materials posted in this section yet.
                  </Text>
                )}
              </Paper>
            );
          })}

          {/* Unassigned materials */}
          {(() => {
            const unassigned = (materials || []).filter((m) => m.section === null);
            if (unassigned.length === 0) return null;
            return (
              <Paper withBorder p="md" radius="md">
                <Title order={3} size="h4" mb="xs">
                  General Course Materials
                </Title>
                <Divider my="sm" />
                <Stack gap="xs">
                  {unassigned.map((m) => (
                    <MaterialItem key={m.id} material={m} />
                  ))}
                </Stack>
              </Paper>
            );
          })()}

          {sections.length === 0 && (!materials || materials.length === 0) && (
            <Paper withBorder p="xl" radius="md" ta="center">
              <Text c="dimmed">No course materials or sections posted yet.</Text>
            </Paper>
          )}
        </Stack>
      )}

      <CreateSectionModal
        opened={sectionModalOpened}
        onClose={() => setSectionModalOpened(false)}
        courseId={courseId}
      />

      <CreateMaterialModal
        opened={materialModalOpened}
        onClose={() => setMaterialModalOpened(false)}
        courseId={courseId}
        sections={sections || []}
      />
    </Stack>
  );
};

export default MaterialsPage;
