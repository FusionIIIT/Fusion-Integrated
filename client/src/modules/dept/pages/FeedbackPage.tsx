import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Modal, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { useFeedbackList, useResolveFeedback, useReviewFeedback, useSubmitFeedback } from "../api/hooks";

export default function FeedbackPage() {
  const { can } = useAuth();
  const { data: feedbackList, isLoading } = useFeedbackList();
  const submitFeedback = useSubmitFeedback();

  const [createOpened, setCreateOpened] = useState(false);
  const [category, setCategory] = useState("ACADEMIC");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const [activeFbId, setActiveFbId] = useState<string | null>(null);
  const reviewMutation = useReviewFeedback(activeFbId ?? "");
  const resolveMutation = useResolveFeedback(activeFbId ?? "");

  const canSubmit = can("dept.feedback.create");
  const canReview = can("dept.feedback.review");
  const canResolve = can("dept.feedback.resolve");

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) return;
    await submitFeedback.mutateAsync({
      category,
      title,
      description,
    });
    setTitle("");
    setDescription("");
    setCreateOpened(false);
  };

  const handleStartReview = async (id: string) => {
    setActiveFbId(id);
    await reviewMutation.mutateAsync({ admin_remarks: "Under active review" });
    setActiveFbId(null);
  };

  const handleResolve = async (id: string, action: "RESOLVE" | "CLOSE") => {
    setActiveFbId(id);
    await resolveMutation.mutateAsync({ action, remarks: `Marked as ${action}` });
    setActiveFbId(null);
  };

  const statusColor = (st: string) => {
    if (st === "RESOLVED") return "green";
    if (st === "CLOSED") return "gray";
    if (st === "UNDER_REVIEW") return "blue";
    return "yellow";
  };

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Feedback</Title>
          <Text c="dimmed">Submit and track academic or infrastructure feedback</Text>
        </div>
        {canSubmit && (
          <Button onClick={() => setCreateOpened(true)}>Submit Feedback</Button>
        )}
      </Group>

      {isLoading && <Text>Loading feedback...</Text>}

      {feedbackList && feedbackList.length === 0 && (
        <Alert title="No Feedback" color="blue">
          There are no feedback submissions recorded.
        </Alert>
      )}

      {feedbackList && feedbackList.length > 0 && (
        <Card withBorder shadow="sm" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Title</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Submitter Role</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Admin Remarks</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {feedbackList.map((fb) => (
                <Table.Tr key={fb.id}>
                  <Table.Td fw={500}>{fb.title}</Table.Td>
                  <Table.Td>
                    <Badge color="cyan">{fb.category}</Badge>
                  </Table.Td>
                  <Table.Td>{fb.submitter_role}</Table.Td>
                  <Table.Td>
                    <Badge color={statusColor(fb.status)}>{fb.status}</Badge>
                  </Table.Td>
                  <Table.Td>{fb.admin_remarks || "-"}</Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      {canReview && fb.status === "NEW" && (
                        <Button size="xs" variant="light" onClick={() => handleStartReview(fb.id)}>
                          Review
                        </Button>
                      )}
                      {canResolve && (fb.status === "NEW" || fb.status === "UNDER_REVIEW") && (
                        <>
                          <Button size="xs" color="teal" onClick={() => handleResolve(fb.id, "RESOLVE")}>
                            Resolve
                          </Button>
                          <Button size="xs" color="gray" variant="subtle" onClick={() => handleResolve(fb.id, "CLOSE")}>
                            Close
                          </Button>
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Submit Feedback">
        <Stack gap="sm">
          <Select
            label="Category"
            data={["ACADEMIC", "INFRASTRUCTURE", "ADMINISTRATIVE", "OTHER"]}
            value={category}
            onChange={(val) => setCategory(val ?? "ACADEMIC")}
            required
          />
          <TextInput label="Title" placeholder="Summary of feedback" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <Textarea label="Description" placeholder="Details of the issue" value={description} onChange={(e) => setDescription(e.target.value)} minRows={3} required />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateOpened(false)}>Cancel</Button>
            <Button onClick={handleSubmit} loading={submitFeedback.isPending}>Submit</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
