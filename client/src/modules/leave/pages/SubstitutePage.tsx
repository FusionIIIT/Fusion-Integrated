import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useLeaveAction } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function SubstitutePage() {
  const { data, isPending, error } = useApplications();
  const action = useLeaveAction();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  const rows = (data?.results ?? []).filter((r) => r.status === "awaiting_substitute");

  function run(id: number, accept: boolean) {
    action.mutate({ id, path: "substitute/respond", body: { accept } }, {
      onSuccess: () => notifications.show({ color: "green", message: "Response recorded" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Substitute tasks" subtitle="Accept or decline nominated responsibility coverage" />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={rows} loading={isPending} rowKey={(r) => r.id}
          columns={[
            { key: "user_id", header: "Applicant", render: (r) => String(r.user_id) },
            { key: "period", header: "Period", render: (r) => `${r.start_on} – ${r.end_on}` },
            { key: "category", header: "Category", render: (r) => r.category },
            {
              key: "actions", header: "",
              render: (r) => (
                <Group gap="xs">
                  <Button size="xs" onClick={() => run(r.id, true)}>Accept</Button>
                  <Button size="xs" color="red" variant="light" onClick={() => run(r.id, false)}>Decline</Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
