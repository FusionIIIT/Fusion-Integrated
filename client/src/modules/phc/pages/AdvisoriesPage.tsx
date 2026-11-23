import { useState } from "react";
import { Button, Card, Container, Stack, Text, TextInput, Textarea } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAdvisories, usePublishAdvisory } from "../api/hooks";
import { ListStates } from "../components/ListStates";
import { LoadMore } from "../components/LoadMore";

export default function AdvisoriesPage() {
  const { can } = useAuth();
  const list = useAdvisories();
  const { data, isPending, error } = list;
  const publish = usePublishAdvisory();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const rows = data?.results ?? [];

  const close = () => {
    setOpen(false);
    setTitle("");
    setBody("");
    publish.reset();
  };

  return (
    <Container size="md">
      <PageHeader
        title="Health advisories"
        subtitle="Notices from the Primary Health Centre"
        action={can("phc.advisory.publish") && (
          <Button onClick={() => setOpen(true)}>Publish advisory</Button>
        )}
      />
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No health advisories yet" />
      <Stack>
        {rows.map((a) => (
          <Card key={a.id} withBorder padding="lg">
            <Text fw={700}>{a.title}</Text>
            <Text size="xs" c="dimmed" mb="xs">{new Date(a.published_at).toLocaleString()}</Text>
            <Text style={{ whiteSpace: "pre-wrap" }}>{a.body}</Text>
          </Card>
        ))}
      </Stack>
      <LoadMore list={list} />
      <FormModal
        opened={open} onClose={close} title="Publish a health advisory"
        submitLabel="Publish" submitting={publish.isPending} error={publish.error}
        disabled={!title.trim() || !body.trim()}
        disabledReason="Enter a title and the advisory text."
        onSubmit={() => publish.mutate({ title, body }, { onSuccess: close })}
      >
        <Stack>
          <TextInput label="Title" required value={title}
            onChange={(e) => setTitle(e.currentTarget.value)} />
          <Textarea label="Advisory" required minRows={4} value={body}
            onChange={(e) => setBody(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </Container>
  );
}
