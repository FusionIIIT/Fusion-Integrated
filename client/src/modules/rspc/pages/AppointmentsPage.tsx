import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, TextInput
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { StaffAppointment } from "../api/types";

export default function AppointmentsPage() {
  const [items, setItems] = useState<StaffAppointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [positionTitle, setPositionTitle] = useState("");
  const [stipend, setStipend] = useState("");
  const [duration, setDuration] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/appointments", { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setItems(data.results ?? data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch("/api/v1/rspc/appointments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          position_title: positionTitle,
          stipend_amount: stipend ? parseFloat(stipend) : null,
          duration_months: duration ? parseInt(duration) : null,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setPositionTitle("");
        setStipend("");
        setDuration("");
        fetchData();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Project Staff Appointments"
        subtitle="Manage JRF/SRF/Research Associate recruitments and stipends"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            Request Appointment
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<StaffAppointment>
          rows={items}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No appointment requests found", description: "Submit an appointment request to get started" }}
          columns={[
            {
              key: "position_title",
              header: "Position Title",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>{r.position_title}</Text>
                  <Text size="xs" c="dimmed">Appt #{r.id}</Text>
                </Stack>
              ),
            },
            {
              key: "stipend",
              header: "Monthly Stipend",
              render: (r) => r.stipend_amount ? `₹${Number(r.stipend_amount).toLocaleString()}/mo` : "—",
            },
            {
              key: "duration",
              header: "Duration",
              render: (r) => r.duration_months ? `${r.duration_months} Months` : "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Requested On",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Request Project Staff Appointment" size="md">
        <Stack gap="sm">
          <TextInput
            label="Position Title"
            required
            placeholder="e.g. Junior Research Fellow (JRF)"
            value={positionTitle}
            onChange={(e) => setPositionTitle(e.target.value)}
          />
          <TextInput
            label="Monthly Stipend (INR)"
            type="number"
            placeholder="e.g. 37000"
            value={stipend}
            onChange={(e) => setStipend(e.target.value)}
          />
          <TextInput
            label="Duration (Months)"
            type="number"
            placeholder="e.g. 12"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
