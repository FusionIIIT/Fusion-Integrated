import { Button, Group, Stack } from "@mantine/core";
import { FaCheck, FaTimes } from "react-icons/fa";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useIndents, useReviewDeptIndent, useReviewPSIndent } from "../api/hooks";
import type { Indent } from "../api/types";

export default function ApprovalQueuePage() {
  const { data: indents = [], isLoading } = useIndents();
  const deptReview = useReviewDeptIndent();
  const psReview = useReviewPSIndent();

  const pendingIndents = indents.filter((i) =>
    ["SUBMITTED", "PENDING_DEPT_APPROVAL", "PENDING_PS_REVIEW", "PENDING_DIRECTOR_APPROVAL"].includes(i.status)
  );

  const handleApprove = async (indent: Indent) => {
    if (indent.status === "PENDING_DEPT_APPROVAL" || indent.status === "SUBMITTED") {
      await deptReview.mutateAsync({ id: indent.id, action: "APPROVE", remarks: "Approved by Dept" });
    } else if (indent.status === "PENDING_PS_REVIEW") {
      await psReview.mutateAsync({ id: indent.id, action: "APPROVE", remarks: "Approved by Stores" });
    }
  };

  const handleReject = async (indent: Indent) => {
    if (indent.status === "PENDING_DEPT_APPROVAL" || indent.status === "SUBMITTED") {
      await deptReview.mutateAsync({ id: indent.id, action: "REJECT", remarks: "Rejected by Dept" });
    } else if (indent.status === "PENDING_PS_REVIEW") {
      await psReview.mutateAsync({ id: indent.id, action: "REJECT", remarks: "Rejected by Stores" });
    }
  };

  const columns: Column<Indent>[] = [
    { key: "indent_number", header: "Indent No." },
    { key: "title", header: "Title" },
    { key: "department_code", header: "Department" },
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
      header: "Review Actions",
      align: "right",
      render: (r) => (
        <Group gap="xs" justify="flex-end">
          <Button
            size="xs"
            color="green"
            variant="light"
            leftSection={<FaCheck size={12} />}
            onClick={() => handleApprove(r)}
            loading={deptReview.isPending || psReview.isPending}
          >
            Approve
          </Button>
          <Button
            size="xs"
            color="red"
            variant="subtle"
            leftSection={<FaTimes size={12} />}
            onClick={() => handleReject(r)}
            loading={deptReview.isPending || psReview.isPending}
          >
            Reject
          </Button>
        </Group>
      ),
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Indent Approval Queue"
        subtitle="Review, endorse, and route pending departmental procurement requests"
      />
      <DataTable
        rows={pendingIndents}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "Approval queue is clear",
          description: "There are currently no indents pending your departmental or administrative review.",
        }}
      />
    </Stack>
  );
}
