import { useState } from "react";
import { Button, Card, Container, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAnnouncements, usePhcPost } from "../api";

export default function AnnouncementsPage() {
  const { data, isPending, error } = useAnnouncements(); const { can } = useAuth();
  const [title, setTitle] = useState(""); const [body, setBody] = useState("");
  const publish = usePhcPost("/phc/announcements");
  if (error) return <Container><ErrorState error={error} /></Container>;
  const submit = async () => { try { await publish.mutateAsync({ title, body }); setTitle(""); setBody("");
    notifications.show({ message: "Announcement published", color: "green" }); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } };
  return <Container size="md"><PageHeader title="PHC Announcements" subtitle="Service updates for institute members" />
    {can("phc.announcement.publish") && <Stack mb="lg"><TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
      <Textarea label="Announcement" minRows={3} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
      <Button disabled={!title || !body} loading={publish.isPending} onClick={submit}>Publish announcement</Button></Stack>}
    {isPending ? <Text c="dimmed">Loading announcements…</Text> : (data?.results ?? []).length === 0 ?
      <Text c="dimmed">No announcements available.</Text> : <Stack>{data?.results.map((a) => <Card key={a.id} withBorder>
        <Text fw={600}>{a.title}</Text><Text mt="xs">{a.body}</Text><Text size="xs" c="dimmed" mt="sm">{new Date(a.created_at).toLocaleString()}</Text>
      </Card>)}</Stack>}
  </Container>;
}
