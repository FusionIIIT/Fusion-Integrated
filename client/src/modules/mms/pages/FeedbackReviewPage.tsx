import { Alert, Card, Container, Stack, Table, Text } from "@mantine/core";
import { FaComments } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFeedback } from "../api/hooks";

export default function FeedbackReviewPage() {
  const { data: feedbackList, isLoading, error } = useFeedback();

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Student Feedback Review" />
      <Stack gap="md">
        <Text size="sm" c="dimmed">Review feedback submitted by students regarding mess food quality and services.</Text>
        <Card withBorder padding="md">
          {isLoading ? (
            <Text c="dimmed">Loading feedback...</Text>
          ) : !feedbackList || feedbackList.length === 0 ? (
            <Alert color="gray" icon={<FaComments />}>No student feedback entries on record.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Student User ID</Table.Th>
                  <Table.Th>Feedback Comments</Table.Th>
                  <Table.Th>Date Submitted</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {feedbackList.map((fb) => (
                  <Table.Tr key={fb.id}>
                    <Table.Td>#{fb.id}</Table.Td>
                    <Table.Td>{fb.student_user_id || fb.user_id}</Table.Td>
                    <Table.Td>{fb.text}</Table.Td>
                    <Table.Td>{new Date(fb.created_at).toLocaleString()}</Table.Td>
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
