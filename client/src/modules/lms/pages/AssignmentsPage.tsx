import React, { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Paper,
  Stack,
  Text,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourseAssignments, useCourseSections } from "../api/hooks";
import type { Assignment } from "../api/types";
import { AssignmentItem } from "../components/AssignmentItem";
import { CreateAssignmentModal } from "../components/CreateAssignmentModal";
import { SubmissionModal } from "../components/SubmissionModal";

export interface AssignmentsPageProps {
  courseId?: number;
  isStudent?: boolean;
}

export const AssignmentsPage: React.FC<AssignmentsPageProps> = ({
  courseId: propCourseId,
  isStudent = false,
}) => {
  const { courseId: paramCourseId } = useParams<{ courseId: string }>();
  const courseId = propCourseId ?? (paramCourseId ? parseInt(paramCourseId) : 0);

  const [createModalOpened, setCreateModalOpened] = useState(false);
  const [submittingAssignment, setSubmittingAssignment] = useState<Assignment | null>(null);

  const {
    data: assignments,
    isLoading: assignmentsLoading,
    error: assignmentsError,
  } = useCourseAssignments(courseId);

  const {
    data: sections,
    isLoading: sectionsLoading,
  } = useCourseSections(courseId);

  const isLoading = assignmentsLoading || sectionsLoading;

  return (
    <Stack gap="lg">
      <PageHeader
        title="Course Assignments"
        subtitle="Homework problems, programming tasks, and course evaluations"
        action={
          !isStudent ? (
            <Group gap="xs">
              <Button variant="filled" size="sm" onClick={() => setCreateModalOpened(true)}>
                Create Assignment
              </Button>
            </Group>
          ) : undefined
        }
      />

      {isLoading && (
        <Center py="xl">
          <Loader size="lg" />
        </Center>
      )}

      {assignmentsError && (
        <Alert color="red" title="Failed to Load Assignments">
          {assignmentsError instanceof Error ? assignmentsError.message : "Unable to load assignments."}
        </Alert>
      )}

      {!isLoading && assignments && assignments.length > 0 && (
        <Stack gap="sm">
          {assignments.map((assignment) => (
            <AssignmentItem
              key={assignment.id}
              assignment={assignment}
              isStudent={isStudent}
              onOpenSubmit={() => setSubmittingAssignment(assignment)}
            />
          ))}
        </Stack>
      )}

      {!isLoading && assignments && assignments.length === 0 && (
        <Paper withBorder p="xl" radius="md" ta="center">
          <Text c="dimmed">No assignments configured for this course yet.</Text>
        </Paper>
      )}

      <CreateAssignmentModal
        opened={createModalOpened}
        onClose={() => setCreateModalOpened(false)}
        courseId={courseId}
        sections={sections || []}
      />

      {submittingAssignment && (
        <SubmissionModal
          opened={Boolean(submittingAssignment)}
          onClose={() => setSubmittingAssignment(null)}
          assignment={submittingAssignment}
        />
      )}
    </Stack>
  );
};

export default AssignmentsPage;
