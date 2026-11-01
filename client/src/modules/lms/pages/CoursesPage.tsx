import { useEffect, useState } from "react";
import { Button, Card, Stack, Text, Title } from "@mantine/core";
import { useNavigate } from "react-router-dom";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { http } from "../../../lib/http";

interface Course {
  source_course_id: string;
  code: string;
  title: string;
  role: string;
}

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    http.get("/lms/courses")
      .then((response) => setCourses(response.data.results ?? []))
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (error) return <ErrorState error={error} />;

  return (
    <Stack>
      <PageHeader title="Courses" subtitle="Your authorized course workspaces" />
      {loading && <Text c="dimmed">Loading courses…</Text>}
      {!loading && courses.length === 0 && (
        <Card padding="lg"><Text c="dimmed">No course workspaces are available.</Text></Card>
      )}
      {courses.map((course) => (
        <Card key={course.source_course_id} padding="lg" withBorder>
          <Stack gap="xs">
            <Title order={4}>{course.code} · {course.title}</Title>
            <Text c="dimmed" size="sm">Role: {course.role.replaceAll("_", " ")}</Text>
            <Button w="fit-content" onClick={() => navigate(
              `/lms/courses/${encodeURIComponent(course.source_course_id)}`)}>
              Open course
            </Button>
          </Stack>
        </Card>
      ))}
    </Stack>
  );
}
