import { Container, Paper, Stack, Text } from "@mantine/core";

import { PageHeader } from "../../ui/components/PageHeader";
import { useNotices } from "./api";
import { FeedState } from "./FeedState";

export default function NoticesPage() {
  const feed = useNotices(15000);
  return (
    <Container size="sm" py="lg">
      <PageHeader title="Department notifications" />
      <Stack>
        {feed.rows.map((notice) => (
          <Paper key={notice.id} withBorder p="md">
            <Text>{notice.message}</Text>
            <Text component="time" dateTime={notice.created_at} c="dimmed" size="sm">
              {new Date(notice.created_at).toLocaleString()}
            </Text>
          </Paper>
        ))}
        <FeedState query={feed} empty="You have no Department notifications." />
      </Stack>
    </Container>
  );
}
