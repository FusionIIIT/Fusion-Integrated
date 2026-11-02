import React from "react";
import { Anchor, Badge, Button, Group, Paper, Text } from "@mantine/core";
import { getFileDownloadUrl } from "../api/hooks";
import type { CourseMaterial } from "../api/types";

export interface MaterialItemProps {
  material: CourseMaterial;
}

export const MaterialItem: React.FC<MaterialItemProps> = ({ material }) => {
  return (
    <Paper withBorder p="md" radius="md" mb="sm">
      <Group justify="space-between" align="center" mb="xs">
        <Text fw={600} size="md">
          {material.title}
        </Text>
        <Group gap="xs">
          <Badge color={material.material_type === "note" ? "blue" : material.material_type === "file" ? "teal" : "violet"}>
            {material.material_type.toUpperCase()}
          </Badge>
          <Badge color={material.is_published ? "green" : "yellow"}>
            {material.is_published ? "Published" : "Draft"}
          </Badge>
        </Group>
      </Group>

      {material.material_type === "note" && material.note_content && (
        <Text size="sm" mt="xs" style={{ whiteSpace: "pre-wrap" }}>
          {material.note_content}
        </Text>
      )}

      {material.material_type === "link" && material.link_url && (
        <Anchor href={material.link_url} target="_blank" rel="noopener noreferrer" size="sm" mt="xs" display="inline-block">
          {material.link_url} ↗
        </Anchor>
      )}

      {material.material_type === "file" && material.file_storage_key && (
        <Button
          component="a"
          href={getFileDownloadUrl(material.file_storage_key)}
          download
          variant="light"
          size="xs"
          mt="xs"
        >
          Download Attachment
        </Button>
      )}
    </Paper>
  );
};

export default MaterialItem;
