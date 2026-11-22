import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Table, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCommentDots } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFeedback, useSubmitFeedback } from "../api/hooks";

export default function FeedbackPage() {
  const { data: feedbackList, isLoading, error } = useFeedback();
  const submitFeedback = useSubmitFeedback();
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      notifications.show({
        color: "red",
        title: "Validation error",
        message: "Please write some feedback before submitting.",
      });
      return;
    }

    submitFeedback.mutate(
      { text: text.trim() },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Feedback Submitted",
            message: "Thank you! Your feedback has been sent to the mess administration.",
          });
          setText("");
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
  };

  if (error) {
    return (
      <Container size="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="md">
      <PageHeader title="Mess Feedback" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              <Text fw={600}>Submit Feedback</Text>
              <Text size="sm" c="dimmed">
                Provide constructive feedback, suggestions, or comments regarding meals and mess operations.
              </Text>
              <Textarea
                placeholder="Share your feedback here..."
                minRows={3}
                required
                value={text}
                onChange={(e) => setText(e.currentTarget.value)}
              />
              <Group justify="flex-end">
                <Button type="submit" loading={submitFeedback.isPending}>
                  Submit Feedback
                </Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">
            My Previous Feedback
          </Text>
          {isLoading ? (
            <Text c="dimmed">Loading feedback...</Text>
          ) : !feedbackList || feedbackList.length === 0 ? (
            <Alert color="gray" icon={<FaCommentDots />}>
              You have not submitted any feedback yet.
            </Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Feedback</Table.Th>
                  <Table.Th>Submitted At</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {feedbackList.map((fb) => (
                  <Table.Tr key={fb.id}>
                    <Table.Td>#{fb.id}</Table.Td>
                    <Table.Td>{fb.text}</Table.Td>
                    <Table.Td>{new Date(fb.created_at).toLocaleDateString()}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
