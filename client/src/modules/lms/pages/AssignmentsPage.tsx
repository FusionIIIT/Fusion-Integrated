import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  FileInput,
  Group,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaClipboardList,
  FaPlus,
  FaUpload,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAssignments,
  useCourses,
  useCreateAssignment,
  usePublishAssignment,
  useSubmitAssignment,
} from "../api/hooks";
import type { Assignment, SubmissionType } from "../api/types";

export default function AssignmentsPage() {
  const { data: courses } = useCourses();
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const activeId = selectedCourseId ?? courses?.[0]?.course_id ?? null;

  const { data: assignments, isPending, error } = useAssignments(activeId);
  const createAssignment = useCreateAssignment();
  const publishAssignment = usePublishAssignment();
  const submitAssignment = useSubmitAssignment();
  const { can } = useAuth();

  const canCreate = can("lms.assignment.create");
  const canPublish = can("lms.assignment.publish");
  const canSubmit = can("lms.submission.create");

  // Create Assignment state
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [pointsPossible, setPointsPossible] = useState("100.00");
  const [submissionType, setSubmissionType] = useState<SubmissionType>("FILE");
  const [dueDate, setDueDate] = useState("");
  const [releaseDate, setReleaseDate] = useState("");

  // Submit Assignment state
  const [submittingTo, setSubmittingTo] = useState<Assignment | null>(null);
  const [contentText, setContentText] = useState("");
  const [contentLink, setContentLink] = useState("");
  const [fileAttachment, setFileAttachment] = useState<File | null>(null);

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

  const handleCreate = () => {
    if (!activeId || !title.trim() || !instructions.trim() || !dueDate) return;

    createAssignment.mutate(
      {
        course_id: activeId,
        title,
        instructions,
        points_possible: pointsPossible,
        submission_type: submissionType,
        due_date: dueDate,
        release_date: releaseDate || null,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Assignment Created",
            message: "Assignment draft created successfully.",
          });
          setCreating(false);
          setTitle("");
          setInstructions("");
          setDueDate("");
          setReleaseDate("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Creation Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  };

  const handlePublish = (assignmentId: number) => {
    publishAssignment.mutate(
      { assignmentId, release_date: null },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Published",
            message: "Assignment is now visible to enrolled students.",
          });
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Publish Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  };

  const handleSubmit = () => {
    if (!submittingTo) return;

    if (submittingTo.submission_type === "FILE") {
      const formData = new FormData();
      formData.append("submission_type", submittingTo.submission_type);
      if (fileAttachment) formData.append("file_attachment", fileAttachment);

      submitAssignment.mutate(
        { assignmentId: submittingTo.id, payload: formData },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Submitted",
              message: "Your submission has been recorded.",
            });
            setSubmittingTo(null);
            setFileAttachment(null);
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Submission Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    } else {
      submitAssignment.mutate(
        {
          assignmentId: submittingTo.id,
          payload: {
            submission_type: submittingTo.submission_type,
            content_text: contentText,
            content_link: contentLink,
          },
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green",
              title: "Submitted",
              message: "Your submission has been recorded.",
            });
            setSubmittingTo(null);
            setContentText("");
            setContentLink("");
          },
          onError: (err) => {
            notifications.show({
              color: "red",
              title: "Submission Failed",
              message: errorMessage(err),
            });
          },
        }
      );
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Assignments"
        subtitle="View lab problems, due dates, and submit work"
        action={
          canCreate && activeId ? (
            <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
              Create Assignment
            </Button>
          ) : undefined
        }
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

      {isPending && <Text c="dimmed">Loading assignments…</Text>}

      {!isPending && (!assignments || assignments.length === 0) && (
        <Card padding="xl" withBorder>
          <Stack align="center" gap={8}>
            <FaClipboardList size={28} color="var(--mantine-color-gray-5)" />
            <Text fw={600}>No assignments posted</Text>
            <Text size="sm" c="dimmed">
              No assignments have been published for this course yet.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {(assignments ?? []).map((ass) => (
          <Card key={ass.id} padding="lg" withBorder>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={6} style={{ flex: 1 }}>
                <Group gap="xs">
                  <Text fw={700} size="md">
                    {ass.title}
                  </Text>
                  <Badge variant="light" color="blue">
                    {ass.points_possible} pts
                  </Badge>
                  <Badge variant="outline" color="gray">
                    Format: {ass.submission_type}
                  </Badge>
                  <Badge
                    size="sm"
                    color={
                      ass.status === "PUBLISHED"
                        ? "green"
                        : ass.status === "SCHEDULED"
                        ? "yellow"
                        : "gray"
                    }
                  >
                    {ass.status}
                  </Badge>
                </Group>

                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  {ass.instructions}
                </Text>

                <Group gap="lg" mt={4}>
                  <Text size="xs" c="dimmed">
                    Due: {new Date(ass.due_date).toLocaleString()}
                  </Text>
                  {ass.release_date && (
                    <Text size="xs" c="dimmed">
                      Release: {new Date(ass.release_date).toLocaleString()}
                    </Text>
                  )}
                </Group>
              </Stack>

              <Group gap="xs">
                {canPublish && ass.status === "DRAFT" && (
                  <Button
                    size="xs"
                    color="teal"
                    onClick={() => handlePublish(ass.id)}
                    loading={publishAssignment.isPending}
                  >
                    Publish
                  </Button>
                )}

                {canSubmit && ass.status === "PUBLISHED" && (
                  <Button
                    size="xs"
                    leftSection={<FaUpload size={10} />}
                    onClick={() => {
                      setSubmittingTo(ass);
                      setContentText("");
                      setContentLink("");
                      setFileAttachment(null);
                    }}
                  >
                    Submit Work
                  </Button>
                )}
              </Group>
            </Group>
          </Card>
        ))}
      </Stack>

      {/* Create Assignment Modal */}
      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Create New Assignment"
        subtitle="Configure assignment instructions, points, and due date"
        onSubmit={handleCreate}
        submitting={createAssignment.isPending}
        submitLabel="Create Assignment"
      >
        <Stack gap="md">
          <TextInput
            label="Assignment Title"
            placeholder="e.g. Lab 1: Socket Programming"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <Textarea
            label="Instructions"
            placeholder="Detailed assignment guidelines and rubric..."
            required
            autosize
            minRows={4}
            value={instructions}
            onChange={(e) => setInstructions(e.currentTarget.value)}
          />
          <Group grow>
            <TextInput
              label="Points Possible"
              type="number"
              required
              value={pointsPossible}
              onChange={(e) => setPointsPossible(e.currentTarget.value)}
            />
            <Select
              label="Submission Format"
              data={[
                { value: "FILE", label: "File Attachment" },
                { value: "TEXT", label: "Inline Text" },
                { value: "LINK", label: "Repository / URL Link" },
              ]}
              value={submissionType}
              onChange={(v) => setSubmissionType((v as SubmissionType) || "FILE")}
              allowDeselect={false}
            />
          </Group>
          <TextInput
            label="Due Date & Time"
            placeholder="YYYY-MM-DDTHH:MM"
            required
            value={dueDate}
            onChange={(e) => setDueDate(e.currentTarget.value)}
          />
          <TextInput
            label="Scheduled Release (Optional)"
            placeholder="YYYY-MM-DDTHH:MM (Leave empty to publish immediately or leave as draft)"
            value={releaseDate}
            onChange={(e) => setReleaseDate(e.currentTarget.value)}
          />
        </Stack>
      </FormModal>

      {/* Submit Assignment Modal */}
      <FormModal
        opened={submittingTo != null}
        onClose={() => setSubmittingTo(null)}
        title={`Submit: ${submittingTo?.title ?? ""}`}
        subtitle={`Required format: ${submittingTo?.submission_type ?? ""}`}
        onSubmit={handleSubmit}
        submitting={submitAssignment.isPending}
        submitLabel="Submit Work"
      >
        <Stack gap="md">
          {submittingTo?.submission_type === "TEXT" && (
            <Textarea
              label="Submission Text"
              placeholder="Paste code or essay response..."
              required
              autosize
              minRows={6}
              value={contentText}
              onChange={(e) => setContentText(e.currentTarget.value)}
            />
          )}

          {submittingTo?.submission_type === "LINK" && (
            <TextInput
              label="Submission URL"
              placeholder="https://github.com/student/my-repo"
              required
              value={contentLink}
              onChange={(e) => setContentLink(e.currentTarget.value)}
            />
          )}

          {submittingTo?.submission_type === "FILE" && (
            <FileInput
              label="Select Submission File"
              placeholder="Upload PDF, archive, or code file"
              required
              value={fileAttachment}
              onChange={setFileAttachment}
            />
          )}
        </Stack>
      </FormModal>
    </Container>
  );
}
