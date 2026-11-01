import { Container, Text } from "@mantine/core";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useInbox } from "../api/hooks";
import type { LeaveTask } from "../api/types";

const InboxPage = () => {
  const { data, isPending, error } = useInbox();
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Leave Inbox" subtitle="Leave tasks currently assigned to you" />
      <DataTable<LeaveTask>
        rows={data?.results ?? []}
        loading={isPending}
        rowKey={(t) => t.task_id}
        minWidth={900}
        empty={{ title: "Nothing in your queue", description: "Leave work assigned to you appears here." }}
        columns={[
          { key: "stage", header: "Stage", render: (t) => t.stage.replace(/_/g, " ") },
          { key: "applicant", header: "Purpose", render: (t) => (
              <Text size="sm" lineClamp={1}>{t.request.purpose}</Text>) },
          { key: "category", header: "Category", render: (t) => t.request.category_label },
          { key: "period", header: "Period", render: (t) => `${t.request.from_date} to ${t.request.to_date}` },
          { key: "status", header: "Status", render: (t) => <StatusBadge status={t.request.status} /> },
          { key: "due", header: "Reminder due", render: (t) => t.reminder_due_at ?? "—" },
        ]}
      />
    </Container>
  );
};

export default InboxPage;
