import { useState } from "react";
import { Button, Card, Container, Group, Modal, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHolidayCalendar, useCreateHoliday, useUpdateHoliday } from "../hooks/useLeaveRequests";
import type { HolidayCalendar } from "../api/types";

export default function HolidayCalendarPage() {
  const notify = notifications;
  const [filters, setFilters] = useState({ year: new Date().getFullYear(), is_restricted: false });
  const { data, isPending, refetch } = useHolidayCalendar(filters);
  const calendar = data ?? { results: [] };
  const createHoliday = useCreateHoliday();
  const updateHoliday = useUpdateHoliday();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingHoliday, setEditingHoliday] = useState<HolidayCalendar | null>(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split("T")[0],
    name: "",
    is_restricted: false,
    year: new Date().getFullYear(),
    is_active: true,
  });

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i);

  const handleOpenCreate = () => {
    setEditingHoliday(null);
    setFormData({
      date: new Date().toISOString().split("T")[0],
      name: "",
      is_restricted: false,
      year: filters.year,
      is_active: true,
    });
    setModalOpen(true);
  };

  const handleOpenEdit = (holiday: HolidayCalendar) => {
    setEditingHoliday(holiday);
    setFormData({
      date: holiday.date,
      name: holiday.name,
      is_restricted: holiday.is_restricted,
      year: holiday.year,
      is_active: holiday.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingHoliday) {
        await updateHoliday.mutateAsync({ id: editingHoliday.id, body: formData });
      } else {
        await createHoliday.mutateAsync(formData);
      }
      notify.show({ title: "Success", message: editingHoliday ? "Holiday updated" : "Holiday created", color: "green" });
      setModalOpen(false);
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to save", color: "red" });
    }
  };

  const handleYearChange = (year: number) => {
    setFilters((p) => ({ ...p, year }));
    setFormData((p) => ({ ...p, year }));
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Holiday & RH Calendar"
        subtitle="Manage holiday and restricted holiday calendar"
        action={
          <Group>
            <select
              value={filters.year}
              onChange={(e) => handleYearChange(Number(e.target.value))}
              className="mantine-Input-input"
              style={{ width: 120, marginRight: 8 }}
            >
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input
                type="checkbox"
                checked={filters.is_restricted}
                onChange={(e) => setFilters((p) => ({ ...p, is_restricted: e.currentTarget.checked }))}
              />
              Restricted Holidays
            </label>
            <Button onClick={handleOpenCreate}>Add Entry</Button>
          </Group>
        }
      />
      <Card padding="lg">
        <DataTable
          rows={calendar.results}
          loading={isPending}
          minWidth={800}
          rowKey={(row) => row.id}
          columns={[
            { key: "date", header: "Date", render: (r) => new Date(r.date).toLocaleDateString() },
            { key: "name", header: "Name" },
            { key: "is_restricted", header: "Type", render: (r) => r.is_restricted ? "Restricted Holiday" : "Holiday" },
            { key: "year", header: "Year" },
            { key: "is_active", header: "Active", render: (r) => r.is_active ? "Yes" : "No" },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group>
                  <Button variant="subtle" size="sm" onClick={() => handleOpenEdit(r)}>Edit</Button>
                </Group>
              ),
            },
          ]}
          empty={{ title: "No holidays", description: "Add holidays for the selected year." }}
        />
      </Card>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editingHoliday ? "Edit Holiday" : "Add Holiday"}>
        <Stack gap="md">
          <input
            type="date"
            value={formData.date}
            onChange={(e) => setFormData((p) => ({ ...p, date: e.currentTarget.value }))}
            className="mantine-Input-input"
            style={{ width: "100%" }}
          />
          <TextInput
            label="Name *"
            placeholder="Holiday name"
            value={formData.name}
            onChange={(e) => setFormData((p) => ({ ...p, name: e.currentTarget.value }))}
            required
          />
          <select
            value={formData.year}
            onChange={(e) => setFormData((p) => ({ ...p, year: Number(e.target.value) }))}
            className="mantine-Input-input"
            style={{ width: "100%" }}
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <Group>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={formData.is_restricted}
                onChange={(e) => setFormData((p) => ({ ...p, is_restricted: e.currentTarget.checked }))}
              />
              Restricted Holiday
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData((p) => ({ ...p, is_active: e.currentTarget.checked }))}
              />
              Active
            </label>
          </Group>
          <Group>
            <Button onClick={handleSubmit} loading={createHoliday.isPending || updateHoliday.isPending}>
              Save
            </Button>
            <Button variant="subtle" onClick={() => setModalOpen(false)}>Cancel</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}