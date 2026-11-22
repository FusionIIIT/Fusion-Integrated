import { Button, Checkbox, Container, Group, Paper, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";
import { useDepartmentAction, useDepartmentFeed } from "./api";
import { useDepartmentCan } from "./DepartmentLayout";
import { FeedState } from "./FeedState";

interface Feedback { id: number; content: string; category: string; status: string }

export function SubmitFeedbackPage() {
  const [content, setContent] = useState("");
  const action = useDepartmentAction();
  return (
    <Container size="sm" py="lg">
      <PageHeader title="Submit feedback" subtitle="Your feedback is visible to the authorised review team." />
      <Paper withBorder p="md" component="form" onSubmit={(event) => {
        event.preventDefault();
        action.mutate({ path: "feedback", data: { content } }, { onSuccess: () => setContent("") });
      }}>
        <Stack>
          <Textarea label="Feedback" value={content} required minRows={5} maxLength={8000}
            onChange={(event) => setContent(event.currentTarget.value)} />
          <Button type="submit" disabled={!content.trim()} loading={action.isPending}>Submit</Button>
          {action.isSuccess && <Text role="status">Feedback submitted.</Text>}
          {action.isError && <ErrorState error={action.error} />}
        </Stack>
      </Paper>
    </Container>
  );
}

function InitialReview({ id }: { id: number }) {
  const [category, setCategory] = useState("");
  const [simple, setSimple] = useState(false);
  const action = useDepartmentAction();
  return (
    <form onSubmit={(event) => {
      event.preventDefault();
      action.mutate({ path: `feedback/${id}/action`, data: {
        action: "review", category, close_simple: simple,
      } });
    }}>
      <Stack>
        <TextInput label="Category" value={category} maxLength={100} required
          onChange={(event) => setCategory(event.currentTarget.value)} />
        <Checkbox label="Close as a simple issue" checked={simple}
          onChange={(event) => setSimple(event.currentTarget.checked)} />
        <Button type="submit" loading={action.isPending} disabled={!category.trim()}>Record review</Button>
        {action.isError && <ErrorState error={action.error} />}
      </Stack>
    </form>
  );
}

export function FeedbackInboxPage() {
  const can = useDepartmentCan();
  const feed = useDepartmentFeed<Feedback>("feedback");
  const action = useDepartmentAction();
  const dispose = (id: number, decision: string) => action.mutate({
    path: `feedback/${id}/action`, data: { action: decision },
  });

  return (
    <Container size="md" py="lg">
      <PageHeader title="Feedback inbox" />
      <Stack>
        {feed.rows.map((item) => (
          <Paper key={item.id} withBorder p="md">
            <Stack>
              <Text size="sm" c="dimmed">#{item.id} · {item.status}{item.category && ` · ${item.category}`}</Text>
              <Text style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{item.content}</Text>
              {item.status === "new" && can("department.feedback.review") && <InitialReview id={item.id} />}
              {item.status === "reviewed" && can("department.feedback.update") && (
                <Group>
                  <Button disabled={action.isPending} onClick={() => dispose(item.id, "resolve")}>Resolve</Button>
                  <Button variant="default" disabled={action.isPending}
                    onClick={() => dispose(item.id, "close")}>Close</Button>
                </Group>
              )}
            </Stack>
          </Paper>
        ))}
        {action.isError && <ErrorState error={action.error} />}
        <FeedState query={feed} empty="There is no feedback to review." />
      </Stack>
    </Container>
  );
}
