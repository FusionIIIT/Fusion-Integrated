import { Alert, Card, Container, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useFeedbackReview } from "../api/hooks";

export default function FeedbackReviewPage() {
  const query = useFeedbackReview();
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  return <Container size="lg"><PageHeader title="Feedback Review" subtitle="Feedback submitted after complaint resolution." />
    {query.isLoading ? <Text c="dimmed">Loading feedback…</Text> : <Stack>{(query.data?.results ?? []).map((row) => <Card withBorder key={row.id}><Text size="xs" c="dimmed">Complaint {row.complaint_reference} · {new Date(row.created_at).toLocaleString()}</Text><Text mt="xs" style={{ whiteSpace: "pre-wrap" }}>{row.message}</Text></Card>)}{!query.data?.results.length && <Alert color="gray">No feedback has been submitted.</Alert>}</Stack>}
  </Container>;
}
