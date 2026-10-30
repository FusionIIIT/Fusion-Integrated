import { useState } from "react";
import {
  Button, Card, Container, Grid, Select, Stack, TextInput, Textarea, Title
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function AdminPage() {
  const [offlineForm, setOfflineForm] = useState({
    user_id: "",
    leave_category: "CL",
    start_date: "",
    end_date: "",
    calculated_days: "1.0",
    reason: "",
    offline_sanction_reference: "",
  });

  const handleRecordOffline = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/v1/elm/admin/offline-record", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...offlineForm,
          user_id: parseInt(offlineForm.user_id),
          calculated_days: parseFloat(offlineForm.calculated_days),
        }),
      });
      if (res.ok) {
        notifications.show({ title: "Success", message: "Offline sanctioned leave recorded." });
        setOfflineForm({
          user_id: "",
          leave_category: "CL",
          start_date: "",
          end_date: "",
          calculated_days: "1.0",
          reason: "",
          offline_sanction_reference: "",
        });
      }
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Leave Administration"
        subtitle="Manage authorized offline leave records and administrative synchronization"
      />

      <Card shadow="sm" padding="lg" withBorder component="form" onSubmit={handleRecordOffline}>
        <Title order={4} mb="md">Record Offline-Sanctioned Leave (Section 12)</Title>
        <Stack gap="md">
          <TextInput
            label="Employee User ID"
            value={offlineForm.user_id}
            onChange={(e) => setOfflineForm({ ...offlineForm, user_id: e.target.value })}
            required
          />
          <Select
            label="Category"
            data={["CL", "RH", "SCL", "EL", "VL", "COL"]}
            value={offlineForm.leave_category}
            onChange={(val) => setOfflineForm({ ...offlineForm, leave_category: val || "CL" })}
          />
          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Start Date"
                type="date"
                value={offlineForm.start_date}
                onChange={(e) => setOfflineForm({ ...offlineForm, start_date: e.target.value })}
                required
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="End Date"
                type="date"
                value={offlineForm.end_date}
                onChange={(e) => setOfflineForm({ ...offlineForm, end_date: e.target.value })}
                required
              />
            </Grid.Col>
          </Grid>
          <TextInput
            label="Total Days Count"
            value={offlineForm.calculated_days}
            onChange={(e) => setOfflineForm({ ...offlineForm, calculated_days: e.target.value })}
            required
          />
          <TextInput
            label="Sanction Reference / File Number"
            placeholder="e.g. EST/LEAVE/2026/042"
            value={offlineForm.offline_sanction_reference}
            onChange={(e) => setOfflineForm({ ...offlineForm, offline_sanction_reference: e.target.value })}
            required
          />
          <Textarea
            label="Remarks / Reference Evidence"
            value={offlineForm.reason}
            onChange={(e) => setOfflineForm({ ...offlineForm, reason: e.target.value })}
          />
          <Button type="submit">Record Offline Leave</Button>
        </Stack>
      </Card>
    </Container>
  );
}
