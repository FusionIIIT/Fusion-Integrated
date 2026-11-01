import { Badge, Button, Card, Container, Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { type AppRow, useApplications } from "../api";

export function ListPage({ title, subtitle }: { title: string; subtitle: string }) {
  const { data, isPending, error } = useApplications();
  const navigate = useNavigate();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title={title} subtitle={subtitle} />
      <Card padding="lg">
        <DataTable<AppRow>
          rows={data ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={720}
          columns={[
            {
              key: "title", header: "Application",
              render: (r) => (
                <div>
                  <Text fw={600}>{r.title}</Text>
                  <Text size="xs" c="dimmed">{r.application_no}</Text>
                </div>
              ),
            },
            {
              key: "status", header: "Status",
              render: (r) => <Badge variant="light">{r.status_label}</Badge>,
            },
            {
              key: "budget", header: "Budget", align: "right",
              render: (r) => (r.budget_total ? `₹ ${r.budget_total}` : "—"),
            },
            {
              key: "open", header: "", align: "right",
              render: (r) => (
                <Button size="xs" variant="light"
                  onClick={() => navigate(`/patents/applications/${r.id}`)}>Open</Button>
              ),
            },
          ]}
          empty={{ title: "Nothing here yet", description: "Applications will appear here." }}
        />
      </Card>
    </Container>
  );
}
