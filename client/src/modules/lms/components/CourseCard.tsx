import React from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Card, Group, Text, Title } from "@mantine/core";
import type { Course } from "../api/types";

export interface CourseCardProps {
  course: Course;
}

export const CourseCard: React.FC<CourseCardProps> = ({ course }) => {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Group justify="space-between" align="center" mb="xs">
        <Text fw={700} size="sm" c="dimmed">
          {course.code}
        </Text>
        <Badge color={course.is_active ? "green" : "gray"}>
          {course.is_active ? "Active" : "Inactive"}
        </Badge>
      </Group>

      <Title order={3} size="h4" mb="xs">
        {course.name}
      </Title>

      <Text size="sm" c="dimmed" mb="sm">
        Academic Year: {course.academic_year} • Semester: {course.semester}
      </Text>

      {course.description && (
        <Text size="sm" lineClamp={2} mb="md">
          {course.description}
        </Text>
      )}

      <Button
        component={Link}
        to={`/courses/${course.id}`}
        fullWidth
        mt="auto"
        variant="light"
      >
        Open Workspace
      </Button>
    </Card>
  );
};

export default CourseCard;
