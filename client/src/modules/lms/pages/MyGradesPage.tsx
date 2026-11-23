import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { FaAward } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAssignments, useCourses, useSubmissions } from "../api/hooks";
import type { Assignment } from "../api/types";

function AssignmentGradeRow({
  assignment,
}: {
  assignment: Assignment;
}) {
  const { data: submissions, isPending } = useSubmissions(assignment.id);
  const mySubmission = (submissions ?? [])[0];

  return (
    <Card padding="md" withBorder>
      <Group justify="space-between" align="center">
        <Stack gap={4}>
          <Group gap="xs">
            <Text fw={600}>{assignment.title}</Text>
            <Badge variant="light" size="sm">
              Max: {assignment.points_possible} pts
            </Badge>
          </Group>
          <Text size="xs" c="dimmed">
            Due: {new Date(assignment.due_date).toLocaleDateString()}
          </Text>
        </Stack>

        <div>
          {isPending && <Text size="xs" c="dimmed">Checking submission…</Text>}

          {!isPending && !mySubmission && (
            <Badge color="red" variant="light">
              Not Submitted
            </Badge>
          )}

          {!isPending && mySubmission && (
            <Group gap="xs">
              <Badge color={mySubmission.status === "SUBMITTED" ? "blue" : "orange"} variant="light">
                {mySubmission.status} (Attempt #{mySubmission.attempt_number})
              </Badge>
            </Group>
          )}
        </div>
      </Group>

      {mySubmission && (
        <Card padding="xs" bg="var(--mantine-color-gray-0)" mt="sm">
          <Text size="xs" c="dimmed">
            Submitted at: {new Date(mySubmission.submitted_at).toLocaleString()}
          </Text>
          {mySubmission.submission_type === "TEXT" && (
            <Text size="xs" mt={2} lineClamp={2}>
              Response: {mySubmission.content_text}
            </Text>
          )}
          {mySubmission.submission_type === "LINK" && (
            <Text size="xs" mt={2}>
              Link: {mySubmission.content_link}
            </Text>
          )}
        </Card>
      )}
    </Card>
  );
}

export default function MyGradesPage() {
  const { data: courses } = useCourses();
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const activeId = selectedCourseId ?? courses?.[0]?.course_id ?? null;

  const { data: assignments, isPending, error } = useAssignments(activeId);

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

  return (
    <Container size="md">
      <PageHeader
        title="My Grades & Submissions"
        subtitle="Review submission standing, scores, and instructor feedback"
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

      {isPending && <Text c="dimmed">Loading grades…</Text>}

      {!isPending && (!assignments || assignments.length === 0) && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={8}>
            <FaAward size={28} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No assignments or grades</Text>
            <Text size="sm" c="dimmed">
              Assignments will appear here once published by your course instructors.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="sm">
        {(assignments ?? []).map((ass) => (
          <AssignmentGradeRow key={ass.id} assignment={ass} />
        ))}
      </Stack>
    </Container>
  );
}
