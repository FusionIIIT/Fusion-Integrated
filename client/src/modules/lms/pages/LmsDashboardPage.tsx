import React from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourses } from "../api/hooks";
import { CourseCard } from "../components/CourseCard";

export const LmsDashboardPage: React.FC = () => {
  const { data: courses, isLoading, isError, error } = useCourses();

  return (
    <Stack gap="lg">
      <PageHeader
        title="LMS Course Management"
        subtitle="Enrolled courses, learning modules, assignments, and announcements"
        action={
          <Group gap="xs">
            <Button
              component={Link}
              to="/courses/scheduled"
              variant="outline"
              size="sm"
            >
              Scheduled Releases
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
        <Alert color="red" title="Failed to Load Courses">
          {error instanceof Error ? error.message : "Unable to retrieve course enrollments."}
        </Alert>
      )}

      {courses && courses.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
          {courses.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </SimpleGrid>
      )}

      {courses && courses.length === 0 && (
        <Paper withBorder p="xl" radius="md" ta="center">
          <Title order={3} size="h4" mb="xs">
            No Enrolled Courses Found
          </Title>
          <Text c="dimmed" size="sm">
            You do not currently have any active course enrollments or instructor assignments.
          </Text>
        </Paper>
      )}
    </Stack>
  );
};

export default LmsDashboardPage;
