import { useState } from "react";
import {
  Button,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  NumberInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { useRequests, useCreateRequest, useSubmitRequest } from "../api/hooks";
import type { ExpenseVoucherRequest } from "../api/types";

export default function RequestsPage() {
  const { data: requests, isPending, error } = useRequests();
  const createMutation = useCreateRequest();
  const submitMutation = useSubmitRequest();
  const { can } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [department, setDepartment] = useState("CSE");
  const [requestType, setRequestType] = useState<"expense" | "voucher">("expense");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState<number>(0);

  const canCreate = can("iaa.request.create");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync({
        department,
        request_type: requestType,
        title,
        description,
        items: [{ description: title || "Initial Item", amount: amount || 0 }],
      });
      notifications.show({ title: "Success", message: "Draft request created successfully." });
      setModalOpen(false);
      setTitle("");
      setDescription("");
      setAmount(0);
    } catch (e: unknown) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Creation failed",
        color: "red",
      });
    }
  };

  const handleSubmit = async (id: number) => {
    try {
      await submitMutation.mutateAsync(id);
      notifications.show({ title: "Submitted", message: "Request formally submitted." });
    } catch (e: unknown) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Submission failed",
        color: "red",
      });
    }
  };

  const columns: Column<ExpenseVoucherRequest>[] = [
    { key: "id", header: "ID", render: (r) => `#${r.id}` },
    { key: "title", header: "Title", render: (r) => r.title },
    { key: "department", header: "Department", render: (r) => r.department },
    { key: "request_type", header: "Type", render: (r) => r.request_type.toUpperCase() },
    { key: "total_amount", header: "Amount", render: (r) => `₹${r.total_amount}` },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    {
      key: "actions",
      header: "Actions",
      render: (r) => (
        <Group gap="xs">
          {r.status === "draft" && (
            <Button size="xs" variant="light" onClick={() => handleSubmit(r.id)} loading={submitMutation.isPending}>
              Submit
            </Button>
          )}
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Expense & Voucher Requests"
          subtitle="Manage institutional expense reimbursements and advance vouchers."
          action={
            canCreate ? (
              <Button onClick={() => setModalOpen(true)}>Create Request</Button>
            ) : undefined
          }
        />

        <DataTable
          rows={requests || []}
          columns={columns}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No financial requests found." }}
        />

        <Modal
          opened={modalOpen}
          onClose={() => setModalOpen(false)}
          title={<Text fw={600}>Create New Request</Text>}
          centered
        >
          <Stack gap="sm">
            <Select
              label="Department"
              data={["CSE", "ECE", "ME", "Design", "Natural Sciences"]}
              value={department}
              onChange={(val) => setDepartment(val || "CSE")}
              required
            />
            <Select
              label="Request Type"
              data={[
                { value: "expense", label: "Expense Reimbursement" },
                { value: "voucher", label: "Advance Voucher" },
              ]}
              value={requestType}
              onChange={(val) => setRequestType((val as "expense" | "voucher") || "expense")}
              required
            />
            <TextInput
              label="Title"
              placeholder="e.g. Lab Equipment Maintenance"
              value={title}
              onChange={(e) => setTitle(e.currentTarget.value)}
              required
            />
            <Textarea
              label="Description"
              placeholder="Provide background details..."
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
            />
            <NumberInput
              label="Initial Amount (₹)"
              value={amount}
              onChange={(val) => setAmount(Number(val) || 0)}
              min={0}
              required
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} loading={createMutation.isPending}>
                Save as Draft
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
