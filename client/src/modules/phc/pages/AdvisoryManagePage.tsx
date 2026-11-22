import { useState } from "react";
import {
  Alert, Button, Card, Container, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaInfoCircle } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAdvisories, usePublishAdvisory } from "../api/hooks";
import type { HealthAdvisory } from "../api/types";

export default function AdvisoryManagePage() {
  const { can } = useAuth();
  const canPublish = can("phc.advisory.publish");
  const canView = can("phc.advisory.view");
  const advisories = useAdvisories(canView);
  const publish = usePublishAdvisory();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [published, setPublished] = useState<HealthAdvisory[]>([]);

  if (canView && advisories.error) {
    return <Container size="xl"><ErrorState error={advisories.error} /></Container>;
  }

  const rows = [
    ...published,
    ...(canView ? advisories.data?.results ?? [] : []),
  ];

  function submit() {
    publish.mutate(
      { title: title.trim(), content: content.trim() },
      {
        onSuccess: (advisory) => {
          setPublished((prev) => [advisory, ...prev]);
          setTitle("");
          setContent("");
          notifications.show({
            color: "green", title: "Advisory published",
            message: "It is now visible on patient dashboards.",
          });
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not publish", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Publish Health Advisory"
        subtitle="Notices appear on the health advisory board for every patient"
      />

      {canPublish ? (
        <Card padding="lg" mb="md">
          {publish.error && <ErrorState error={publish.error} />}
          <Stack gap="md">
            <TextInput
              label="Title" required value={title}
              onChange={(e) => setTitle(e.currentTarget.value)} maxLength={160}
            />
            <Textarea
              label="Content" required autosize minRows={5} value={content}
              onChange={(e) => setContent(e.currentTarget.value)}
            />
            <Button
              onClick={submit} loading={publish.isPending}
              disabled={!title.trim() || !content.trim()}
            >
              Publish advisory
            </Button>
          </Stack>
        </Card>
      ) : (
        <Alert variant="light" color="red" mb="md">
          You do not have permission to publish advisories.
        </Alert>
      )}

      {!canView && (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
          <Text size="sm">
            The published list needs the advisory-view permission. Advisories
            published here are still shown below.
          </Text>
        </Alert>
      )}

      <Card padding="lg">
        <DataTable<HealthAdvisory>
          rows={rows}
          loading={canView && advisories.isPending}
          rowKey={(r) => r.id}
          minWidth={820}
          columns={[
            { key: "title", header: "Title",
              render: (r) => <Text fw={600}>{r.title}</Text> },
            { key: "content", header: "Content",
              render: (r) => <Text size="sm" lineClamp={2}>{r.content}</Text> },
            { key: "published_at", header: "Published",
              render: (r) => r.published_at
                ? new Date(r.published_at).toLocaleString() : "—" },
            { key: "published_by", header: "By",
              render: (r) => r.published_by ?? "—" },
          ]}
          empty={{
            icon: FaBullhorn,
            title: "No advisories published",
            description: "Published notices will be listed here.",
          }}
        />
      </Card>
    </Container>
  );
}
