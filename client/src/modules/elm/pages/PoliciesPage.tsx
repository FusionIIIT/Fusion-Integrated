import {
  Badge, Button, Card, Container, Group, JsonInput, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreatePolicy, usePolicies, usePublishPolicy } from "../api/hooks";

export default function PoliciesPage() {
  const { data, isPending, error } = usePolicies();
  const create = useCreatePolicy();
  const publish = usePublishPolicy();
  const [draft, setDraft] = useState<{ name: string; from: string; params: string;
    hierarchy: string } | null>(null);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  const rows = data?.results ?? [];

  function startDraft() {
    const base = rows.find((r) => r.status === "published") ?? rows[0];
    setDraft({ name: "", from: "",
      params: JSON.stringify(base?.params ?? {}, null, 2),
      hierarchy: JSON.stringify(base?.hierarchy ?? {}, null, 2) });
  }

  function save() {
    if (!draft) return;
    let params, hierarchy;
    try {
      params = JSON.parse(draft.params);
      hierarchy = JSON.parse(draft.hierarchy);
    } catch {
      notifications.show({ color: "red", title: "Invalid JSON", message: "Fix the JSON first." });
      return;
    }
    create.mutate({ name: draft.name, effective_from: draft.from, params, hierarchy }, {
      onSuccess: () => setDraft(null),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Policy"
        subtitle="Entitlements and the approval hierarchy. Published versions are never edited."
        action={<Button onClick={startDraft}>New version</Button>} />
      <Card withBorder padding="md">
        <DataTable rows={rows} loading={isPending} rowKey={(r) => r.id}
          empty={{ title: "No policy versions",
            description: "Nothing can be applied for until a policy is published." }}
          columns={[
            { key: "name", header: "Version", render: (r) => <Text size="sm">#{r.id} {r.name}</Text> },
            { key: "from", header: "Effective from", render: (r) => r.effective_from },
            { key: "status", header: "Status",
              render: (r) => <Badge color={r.status === "published" ? "green" : "gray"}
                variant="light">{r.status}</Badge> },
            { key: "act", header: "", align: "right",
              render: (r) => r.status === "draft" && (
                <Button size="xs" loading={publish.isPending}
                  onClick={() => publish.mutate(r.id, {
                    onError: (e) => notifications.show({ color: "red",
                      title: "Not published", message: errorMessage(e) }) })}>
                  Publish</Button>) },
          ]} />
      </Card>
      {draft && (
        <FormModal opened title="New policy version" onClose={() => setDraft(null)}
          size="xl" submitting={create.isPending} error={create.error}
          disabled={!draft.name || !draft.from} onSubmit={save} submitLabel="Save draft">
          <Stack>
            <Group grow>
              <TextInput label="Name" value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.currentTarget.value })} />
              <TextInput type="date" label="Effective from" value={draft.from}
                onChange={(e) => setDraft({ ...draft, from: e.currentTarget.value })} />
            </Group>
            <JsonInput label="Parameters" autosize minRows={8} formatOnBlur
              value={draft.params} onChange={(params) => setDraft({ ...draft, params })} />
            <JsonInput label="Hierarchy" autosize minRows={8} formatOnBlur
              value={draft.hierarchy} onChange={(hierarchy) => setDraft({ ...draft, hierarchy })} />
          </Stack>
        </FormModal>
      )}
    </Container>
  );
}
