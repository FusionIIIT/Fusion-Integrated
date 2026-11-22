import React from "react";
import { Badge, Group, Paper, Text } from "@mantine/core";
import type { Announcement } from "../api/types";

export interface AnnouncementItemProps {
  announcement: Announcement;
}

export const AnnouncementItem: React.FC<AnnouncementItemProps> = ({ announcement }) => {
  const formattedDate = announcement.created_at
    ? new Date(announcement.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "";

  return (
    <Paper withBorder p="md" radius="md" mb="sm">
      <Group justify="space-between" align="center" mb="xs">
        <Text fw={600} size="md">
          {announcement.title}
        </Text>
        {announcement.is_pinned && <Badge color="blue">Pinned</Badge>}
      </Group>

      <Text size="xs" c="dimmed" mb="xs">
        By {announcement.author_role?.toUpperCase() || "INSTRUCTOR"} • {formattedDate}
      </Text>

      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
        {announcement.content}
      </Text>
    </Paper>
  );
};

export default AnnouncementItem;
