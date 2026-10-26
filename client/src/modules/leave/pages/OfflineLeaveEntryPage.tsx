import { useState } from "react";
import { Button, Card, Container, Group, Modal, Select, Stack, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useOfflineLeaveEntries, useCreateOfflineLeaveEntry } from "../hooks/useLeaveRequests";
import type { LeaveCategory } from "../api/types";

const CATEGORIES: { value: LeaveCategory; label: string }[] = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
];

export default function OfflineLeaveEntryPage() {
  const notify = notifications;
  const { data, isPending, refetch } = useOfflineLeaveEntries();
  const offlineEntries = data ?? { results: [] };
  const createOfflineEntry = useCreateOfflineLeaveEntry();

  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    user_id: "",
    category: "CL" as LeaveCategory,
    start_date: new Date().toISOString().split("T")[0],
    end_date: new Date().toISOString().split("T")[0],
    total_days: "",
    sanction_order_number: "",
    sanction_order_date: new Date().toISOString().split("T")[0],
    sanctioning_authority: "",
    remarks: "",
  });

  const handleOpenCreate = () => {
    setFormData({
      user_id: "",
      category: "CL",
      start_date: new Date().toISOString().split("T")[0],
      end_date: new Date().toISOString().split("T")[0],
      total_days: "",
      sanction_order_number: "",
      sanction_order_date: new Date().toISOString().split("T")[0],
      sanctioning_authority: "",
      remarks: "",
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      await createOfflineEntry.mutateAsync({
        ...formData,
        user_id: Number(formData.user_id),
      });
      notify.show({ title: "Success", message: "Offline leave entry recorded", color: "green" });
      setModalOpen(false);
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to record entry", color: "red" });
    }
  };

  return (
    <Container size="xl">
      <PageHeader title="Record Offline Leave" subtitle="Record previously sanctioned leave entries" action={<Button onClick={handleOpenCreate}>Record Entry</Button>} />
      <Card padding="lg">
        <DataTable
          rows={offlineEntries.results}
          loading={isPending}
          minWidth={1000}
          rowKey={(row) => row.id}
          columns={[
            { key: "user_id", header: "Employee ID" },
            { key: "category", header: "Category" },
            {
              key: "start_date",
              header: "From",
              render: (r) => new Date(r.start_date).toLocaleDateString(),
            },
            {
              key: "end_date",
              header: "To",
              render: (r) => new Date(r.end_date).toLocaleDateString(),
            },
            { key: "total_days", header: "Days" },
            { key: "sanction_order_number", header: "Sanction Order No." },
            { key: "sanction_order_date", header: "Sanction Date", render: (r) => new Date(r.sanction_order_date).toLocaleDateString() },
            { key: "sanctioning_authority", header: "Sanctioning Authority" },
            { key: "entered_by", header: "Entered By" },
            { key: "verified", header: "Verified", render: (r) => r.verified ? "Yes" : "No" },
            { key: "created_at", header: "Recorded At", render: (r) => new Date(r.created_at).toLocaleDateString() },
          ]}
          empty={{ title: "No offline entries", description: "Record offline-sanctioned leave entries here." }}
        />
      </Card>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Record Offline Leave Entry">
        <Stack gap="md">
          <TextInput
            label="Employee ID *"
            type="number"
            placeholder="Enter employee ID"
            value={formData.user_id}
            onChange={(e) => setFormData((p) => ({ ...p, user_id: e.currentTarget.value }))}
            required
          />
          <Select
            label="Category *"
            placeholder="Select category"
            value={formData.category}
            onChange={(v) => setFormData((p) => ({ ...p, category: v as LeaveCategory }))}
            data={CATEGORIES}
            required
          />
          <Group>
            <input
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData((p) => ({ ...p, start_date: e.currentTarget.value }))}
              className="mantine-Input-input"
              style={{ width: "100%" }}
            />
            <input
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData((p) => ({ ...p, end_date: e.currentTarget.value }))}
              className="mantine-Input-input"
              style={{ width: "100%" }}
            />
          </Group>
          <TextInput
            label="Total Days *"
            type="number"
            step="0.5"
            placeholder="Enter total days"
            value={formData.total_days}
            onChange={(e) => setFormData((p) => ({ ...p, total_days: e.currentTarget.value }))}
            required
          />
          <TextInput
            label="Sanction Order Number *"
            placeholder="Enter sanction order number"
            value={formData.sanction_order_number}
            onChange={(e) => setFormData((p) => ({ ...p, sanction_order_number: e.currentTarget.value }))}
            required
          />
          <input
            type="date"
            value={formData.sanction_order_date}
            onChange={(e) => setFormData((p) => ({ ...p, sanction_order_date: e.currentTarget.value }))}
            className="mantine-Input-input"
            style={{ width: "100%" }}
          />
          <TextInput
            label="Sanctioning Authority *"
            placeholder="Enter sanctioning authority name"
            value={formData.sanctioning_authority}
            onChange={(e) => setFormData((p) => ({ ...p, sanctioning_authority: e.currentTarget.value }))}
            required
          />
          <Textarea
            label="Remarks"
            placeholder="Enter remarks"
            value={formData.remarks}
            onChange={(e) => setFormData((p) => ({ ...p, remarks: e.currentTarget.value }))}
            minRows={3}
          />
          <Group>
            <Button onClick={handleSubmit} loading={createOfflineEntry.isPending}>
              Save
            </Button>
            <Button variant="subtle" onClick={() => setModalOpen(false)}>Cancel</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}