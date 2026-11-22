import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements, usePublishAnnouncement } from "../api/hooks";

const PUBLISH = "complaints.announcement.publish";

export default function AnnouncementsPage() {
  const { can } = useAuth();
  const query = useAnnouncements();
  const publish = usePublishAnnouncement();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  function save() {
    publish.mutate({ title, body }, {
      onSuccess: () => { setTitle(""); setBody(""); notifications.show({ color: "green", title: "Announcement published", message: "It is now visible to users." }); },
      onError: (e) => notifications.show({ color: "red", title: "Could not publish", message: errorMessage(e) }),
    });
  }
  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  return <Container size="lg"><PageHeader title="Announcements" subtitle="Updates from the Complaint Management System." />
    {can(PUBLISH) && <Card withBorder padding="lg" mb="lg"><Stack><Text fw={600}>Publish an announcement</Text><TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} required /><Textarea label="Announcement" minRows={3} autosize value={body} onChange={(e) => setBody(e.currentTarget.value)} required /><Group justify="flex-end"><Button onClick={save} loading={publish.isPending} disabled={!title.trim() || !body.trim()}>Publish</Button></Group></Stack></Card>}
    <Stack>{(query.data?.results ?? []).map((item) => <Card key={item.id} withBorder padding="lg"><Text fw={600}>{item.title}</Text><Text size="xs" c="dimmed" mb="sm">{item.published_at ? new Date(item.published_at).toLocaleString() : ""}</Text><Text style={{ whiteSpace: "pre-wrap" }}>{item.body}</Text></Card>)}{query.isLoading && <Text c="dimmed">Loading announcements…</Text>}{!query.isLoading && !query.data?.results.length && <Alert color="gray">There are no published announcements.</Alert>}</Stack>
  </Container>;
}
