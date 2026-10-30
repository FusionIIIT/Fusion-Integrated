import { useState } from "react";
import {
  Button, Card, Checkbox, Container, Grid, Select, Stack, TextInput, Textarea, Title
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    leave_category: "CL",
    start_date: "",
    end_date: "",
    half_day_type: "",
    reason: "",
    substitute_user_id: "",
    is_station_leave: false,
    station_start_date: "",
    station_end_date: "",
    station_destination: "",
    station_contact_address: "",
    station_emergency_phone: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = {
        leave_category: form.leave_category,
        start_date: form.start_date,
        end_date: form.end_date,
        half_day_type: form.half_day_type,
        reason: form.reason,
        substitute_user_id: form.substitute_user_id ? parseInt(form.substitute_user_id) : null,
        is_station_leave: form.is_station_leave,
      };
      if (form.is_station_leave) {
        payload.station_start_date = form.station_start_date;
        payload.station_end_date = form.station_end_date;
        payload.station_destination = form.station_destination;
        payload.station_contact_address = form.station_contact_address;
        payload.station_emergency_phone = form.station_emergency_phone;
      }

      const res = await fetch("/api/v1/elm/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        notifications.show({ title: "Success", message: "Leave application submitted." });
        navigate("/elm/my-leaves");
      } else {
        const err = await res.json();
        notifications.show({ title: "Error", message: JSON.stringify(err), color: "red" });
      }
    } catch (e: any) {
      notifications.show({ title: "Error", message: e.message, color: "red" });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Apply Leave"
        subtitle="Submit a leave application with mandatory substitute and station leave options"
      />

      <Card shadow="sm" padding="lg" withBorder component="form" onSubmit={handleSubmit}>
        <Stack gap="md">
          <Select
            label="Leave Category"
            data={["CL", "RH", "SCL", "EL", "VL", "COL"]}
            value={form.leave_category}
            onChange={(val) => setForm({ ...form, leave_category: val || "CL" })}
            required
          />

          <Grid>
            <Grid.Col span={6}>
              <TextInput
                label="Start Date"
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                required
              />
            </Grid.Col>
            <Grid.Col span={6}>
              <TextInput
                label="End Date"
                type="date"
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                required
              />
            </Grid.Col>
          </Grid>

          {form.leave_category === "CL" && (
            <Select
              label="Half-Day Option"
              data={[
                { value: "", label: "Full Day" },
                { value: "first_half", label: "First Half (0.5 day)" },
                { value: "second_half", label: "Second Half (0.5 day)" },
              ]}
              value={form.half_day_type}
              onChange={(val) => setForm({ ...form, half_day_type: val || "" })}
            />
          )}

          <TextInput
            label="Nominated Substitute (User ID)"
            placeholder="Enter employee User ID if responsibility coverage needed"
            value={form.substitute_user_id}
            onChange={(e) => setForm({ ...form, substitute_user_id: e.target.value })}
          />

          <Textarea
            label="Purpose / Reason"
            value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.target.value })}
            required
          />

          <Checkbox
            label="I will be leaving Jabalpur (Include Station Leave)"
            checked={form.is_station_leave}
            onChange={(e) => setForm({ ...form, is_station_leave: e.currentTarget.checked })}
          />

          {form.is_station_leave && (
            <Card withBorder bg="gray.0" padding="md">
              <Title order={5} mb="xs">Station Leave Details</Title>
              <Grid>
                <Grid.Col span={6}>
                  <TextInput
                    label="Station Start Date"
                    type="date"
                    value={form.station_start_date}
                    onChange={(e) => setForm({ ...form, station_start_date: e.target.value })}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="Station End Date"
                    type="date"
                    value={form.station_end_date}
                    onChange={(e) => setForm({ ...form, station_end_date: e.target.value })}
                  />
                </Grid.Col>
                <Grid.Col span={12}>
                  <TextInput
                    label="Destination"
                    value={form.station_destination}
                    onChange={(e) => setForm({ ...form, station_destination: e.target.value })}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="Contact Address"
                    value={form.station_contact_address}
                    onChange={(e) => setForm({ ...form, station_contact_address: e.target.value })}
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="Emergency Phone"
                    value={form.station_emergency_phone}
                    onChange={(e) => setForm({ ...form, station_emergency_phone: e.target.value })}
                  />
                </Grid.Col>
              </Grid>
            </Card>
          )}

          <Button type="submit" mt="md">Submit Application</Button>
        </Stack>
      </Card>
    </Container>
  );
}
