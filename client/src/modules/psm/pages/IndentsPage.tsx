import { ActionIcon, Button, Group, Stack } from "@mantine/core";
import { FaEye, FaPlus } from "react-icons/fa";
import { Link } from "react-router-dom";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useIndents } from "../api/hooks";
import type { Indent } from "../api/types";

export default function IndentsPage() {
  const { data: indents = [], isLoading } = useIndents();

  const columns: Column<Indent>[] = [
    { key: "indent_number", header: "Indent No." },
    { key: "title", header: "Title" },
    { key: "department_code", header: "Department" },
    { key: "priority", header: "Priority" },
    {
      key: "estimated_total",
      header: "Estimated Total (₹)",
      align: "right",
      render: (r) => `₹${Number(r.estimated_total).toLocaleString("en-IN")}`,
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (r) => (
        <Group gap="xs" justify="flex-end">
          <ActionIcon component={Link} to={`/psm/indents/${r.id}`} variant="subtle" color="gray">
            <FaEye size={14} />
          </ActionIcon>
        </Group>
      ),
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Purchase Indents"
        subtitle="Manage and track procurement indents across departments"
        action={
          <Button component={Link} to="/psm/indents/new" leftSection={<FaPlus size={14} />}>
            Raise Indent
          </Button>
        }
      />
      <DataTable
        rows={indents}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No purchase indents found",
          description: "Get started by raising a new procurement indent for your department.",
        }}
      />
    </Stack>
  );
}
