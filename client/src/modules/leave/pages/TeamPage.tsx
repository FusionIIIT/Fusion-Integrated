import { useState } from "react";
import { Container, Select, Stack } from "@mantine/core";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAllRequests } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { Text } from "@mantine/core";

const TeamPage = () => {
  const [status, setStatus] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);

  const filters = { status: status ?? undefined, category: category ?? undefined };

  const { data, isPending, error } = useAllRequests(filters);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="All Leave" subtitle="Every leave request, filtered" />
      <Stack gap="md">
        <Select
          label="Status"
          placeholder="Select status"
          clearable
          data={["draft", "awaiting_unit_head", "awaiting_establishment", "awaiting_final", "approved", "rejected", "withdrawn", "cancelled", "resumed"]}
          value={status}
          onChange={(value) => setStatus(value)}
        />
        <Select
          label="Category"
          placeholder="Select category"
          clearable
          data={[
            { value: "cl", label: "Casual Leave" },
            { value: "rh", label: "Restricted Holiday" },
            { value: "scl", label: "Special Casual Leave" },
            { value: "el", label: "Earned Leave" },
            { value: "col", label: "Commuted Leave" },
            { value: "vl", label: "Vacation Leave" },
          ]}
          value={category}
          onChange={(value) => setCategory(value)}
        />
      </Stack>
      <DataTable<LeaveRequest>
        rows={data?.results ?? []}
        loading={isPending}
        rowKey={(r) => r.id}
        minWidth={900}
        empty={{ title: "No leave requests", description: "Nothing matches these filters yet." }}
        columns={[
          { key: "category", header: "Category", render: (r) => r.category_label },
          { key: "period", header: "Period", render: (r) => `${r.from_date} to ${r.to_date}` },
          { key: "days", header: "Days", align: "right", render: (r) => r.days },
          { key: "purpose", header: "Purpose", render: (r) => <Text>{r.purpose}</Text> },
          { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
        ]}
      />
    </Container>
  );
};

export default TeamPage;
