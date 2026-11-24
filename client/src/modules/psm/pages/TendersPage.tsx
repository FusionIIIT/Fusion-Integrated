// Competitive tender management, bid recording, evaluation, and committee award (PSM-UC-022).
import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateTender, useTenderAction, useTenders } from "../api/hooks";
import type { Tender } from "../api/types";

export default function TendersPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useTenders();
  const createTender = useCreateTender();
  const act = useTenderAction();

  const [creating, setCreating] = useState(false);
  const [indentId, setIndentId] = useState<number | string>(1);
  const [title, setTitle] = useState("");
  const [scope, setScope] = useState("");
  const [criteria, setCriteria] = useState("");
  const [deadline, setDeadline] = useState("2030-01-01T12:00:00Z");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Tenders"
        subtitle="Publish tender invitations, record bids, evaluate, and record committee award"
        action={can("psm.tender.create") ? <Button onClick={() => setCreating(true)}>New tender</Button> : undefined}
      />

      <Card padding="lg">
        <DataTable<Tender>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No tenders found." }}
          columns={[
            {
              key: "number",
              header: "Tender",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.tender_number}</Text>
                  <Text size="xs" c="dimmed">{r.title}</Text>
                </Stack>
              ),
            },
            { key: "bids", header: "Bids", render: (r) => r.bids.length },
            { key: "status", header: "Status", render: (r) => <Badge variant="light">{r.status}</Badge> },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {can("psm.tender.publish") && r.status === "draft" && (
                    <Button
                      size="xs"
                      onClick={() =>
                        act.mutate(
                          { id: r.id, action: "publish" },
                          {
                            onSuccess: () => notifications.show({ color: "green", title: "Published", message: `${r.tender_number} published.` }),
                            onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
                          },
                        )
                      }
                    >
                      Publish
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Create Tender"
        submitLabel="Create tender"
        submitting={createTender.isPending}
        onSubmit={() =>
          createTender.mutate(
            { indent_id: Number(indentId), title, scope, evaluation_criteria: criteria, submission_deadline: deadline },
            {
              onSuccess: () => {
                setCreating(false);
                setTitle("");
                notifications.show({ color: "green", title: "Created", message: "Draft tender saved." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="Indent ID" value={indentId} onChange={setIndentId} required />
          <TextInput label="Tender title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} required />
          <Textarea label="Scope" value={scope} onChange={(e) => setScope(e.currentTarget.value)} required />
          <Textarea label="Evaluation criteria" value={criteria} onChange={(e) => setCriteria(e.currentTarget.value)} required />
          <TextInput label="Submission deadline (ISO)" value={deadline} onChange={(e) => setDeadline(e.currentTarget.value)} required />
        </Stack>
      </FormModal>
    </Container>
  );
}
