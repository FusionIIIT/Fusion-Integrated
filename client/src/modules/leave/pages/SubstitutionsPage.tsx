import { Button, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { errorMessage } from "../../../lib/http";
import { useRespond, useSubstitutions } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

const SubstitutionsPage = () => {
  const { data, isPending, error } = useSubstitutions();
  const respond = useRespond();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function act(r: LeaveRequest, accept: boolean) {
    respond.mutate({ id: r.id, accept }, {
      onSuccess: () => notifications.show({
        color: accept ? "green" : "gray",
        title: accept ? "Accepted" : "Declined",
        message: accept ? "You are now the substitute for this leave."
                        : "You have declined this substitution.",
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not record your response",
        message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Substitutions" subtitle="Leave requests where you are the nominated substitute" />
      <DataTable<LeaveRequest>
         rows={data?.results ?? []}
         loading={isPending}
         rowKey={(r) => r.id}
         minWidth={820}
         empty={{ title: "No substitutions", description: "Requests naming you as substitute appear here." }}
         columns={[
           { key: "category", header: "Category", render: (r) => r.category_label },
           { key: "period", header: "Period", render: (r) => `${r.from_date} to ${r.to_date}` },
           { key: "days", header: "Days", align: "right", render: (r) => r.days },
           { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
           { key: "actions", header: "", render: (r) => (
               <Group gap="xs" justify="flex-end">
                 <Button size="xs" color="green" onClick={() => act(r, true)}>Accept</Button>
                 <Button size="xs" color="red" variant="light" onClick={() => act(r, false)}>Decline</Button>
               </Group>
             ) },
         ]}
      />
    </Container>
  );
};

export default SubstitutionsPage;
