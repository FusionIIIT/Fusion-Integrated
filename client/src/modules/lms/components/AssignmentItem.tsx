import React from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Group, Paper, Stack, Text, Title } from "@mantine/core";
import type { Assignment } from "../api/types";

export interface AssignmentItemProps {
  assignment: Assignment;
  onOpenSubmit?: () => void;
  isStudent?: boolean;
}

export const AssignmentItem: React.FC<AssignmentItemProps> = ({
  assignment,
  onOpenSubmit,
  isStudent,
}) => {
  const formattedDueDate = assignment.due_date
    ? new Date(assignment.due_date).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "No due date";

  return (
    <Paper withBorder p="md" radius="md" mb="sm">
      <Group justify="space-between" align="flex-start" mb="xs">
        <Stack gap={2}>
          <Title order={4} size="h5">
            {assignment.title}
          </Title>
          <Text size="xs" c="dimmed">
            Due: {formattedDueDate}
          </Text>
        </Stack>

        <Group gap="xs">
          <Badge variant="outline" color="blue">
            {assignment.points_possible} pts
          </Badge>
          <Badge variant="outline" color="cyan">
            {assignment.submission_type.toUpperCase()}
          </Badge>
          <Badge color={assignment.is_published ? "green" : "yellow"}>
            {assignment.is_published ? "Published" : "Draft"}
          </Badge>
        </Group>
      </Group>

      {assignment.description && (
        <Text size="sm" lineClamp={2} mb="md">
          {assignment.description}
        </Text>
      )}

      <Group justify="flex-end" mt="md" gap="xs">
        {isStudent && onOpenSubmit && (
          <Button onClick={onOpenSubmit} size="xs" variant="filled">
            Submit Assignment
          </Button>
        )}
        <Button
          component={Link}
          to={`/courses/${assignment.course}/assignments/${assignment.id}`}
          size="xs"
          variant="light"
        >
          View Details
        </Button>
      </Group>
    </Paper>
  );
};

export default AssignmentItem;
