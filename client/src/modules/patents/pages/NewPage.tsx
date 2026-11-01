import { useState } from "react";
import { Button, Card, Container, Group, Stack, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateApplication } from "../api";

export default function NewPage() {
  const navigate = useNavigate();
  const create = useCreateApplication();
  const [form, setForm] = useState({ title: "", domain: "", abstract: "", description: "", claims: "" });

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.currentTarget.value }));
  }

  function save() {
    create.mutate(form, {
      onSuccess: (app) => {
        notifications.show({ color: "green", title: "Draft saved", message: app.application_no });
        navigate(`/patents/applications/${app.id}`);
      },
      onError: (e) => notifications.show({ color: "red", title: "Could not save", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="md">
      <PageHeader title="New application" subtitle="Save a draft, then submit it from its page" />
      <Card padding="lg">
        <Stack gap="md">
          <TextInput label="Title" value={form.title} onChange={set("title")} required />
          <TextInput label="Domain" value={form.domain} onChange={set("domain")} />
          <Textarea label="Abstract" value={form.abstract} onChange={set("abstract")} autosize minRows={3} />
          <Textarea label="Detailed description" value={form.description} onChange={set("description")} autosize minRows={6} />
          <Textarea label="Claims" value={form.claims} onChange={set("claims")} autosize minRows={4} />
          <Group justify="flex-end">
            <Button loading={create.isPending} disabled={!form.title} onClick={save}>Save draft</Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
