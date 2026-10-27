import { useState } from "react";
import { Button, Card, Checkbox, Container, Group, NumberInput, Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CATEGORY_LABELS, useApply, type HalfDay, type LeaveCategory } from "../api";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const submitMutation = useApply();
  const [category, setCategory] = useState<LeaveCategory>("CL");
  const [formData, setFormData] = useState({
    start_date: "",
    end_date: "",
    half_day: "none" as HalfDay,
    purpose: "",
    station_leave: false,
    station_address: "",
    substitute_id: "",
  });

  // Update half_day when category changes to CL and dates are equal
  const isSingleDay = formData.start_date && formData.end_date && formData.start_date === formData.end_date;
  const showHalfDaySelect = category === "CL" && isSingleDay;

  const handleCategoryChange = (value: LeaveCategory) => {
    setCategory(value);
    // Reset half_day when switching categories to ensure consistency
    if (value === "CL") {
      setFormData((prev) => ({ ...prev, half_day: "none" as HalfDay }));
    } else {
      setFormData((prev) => ({ ...prev, half_day: "none" as HalfDay }));
    }
  };

  const handleSubmit = () => {
    // Validation checks
    if (!formData.start_date || !formData.end_date || !formData.purpose) {
      notifications.show({
        color: "red",
        title: "Missing Information",
        message: "Please fill in all required fields.",
      });
      return;
    }

    submitMutation.mutate(
      {
        category,
        start_date: formData.start_date,
        end_date: formData.end_date,
        half_day: showHalfDaySelect ? formData.half_day : "none",
        purpose: formData.purpose,
        station_leave: formData.station_leave,
        station_address: formData.station_address,
        substitute_id: formData.substitute_id ? Number(formData.substitute_id) : null,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Application Submitted",
            message: "Your leave application has been submitted successfully.",
          });
          navigate("/leave/mine");
        },
        onError: (e) => {
          notifications.show({
            color: "red",
            title: "Submission Failed",
            message: errorMessage(e),
          });
        },
      }
    );
  };

  return (
    <Container size="xl">
      <PageHeader title="Apply for Leave" subtitle="Submit a new leave request" />
      <Card padding="lg">
        <Stack gap="md">
          <Group justify="space-between" align="flex-end">
            <Select
              label="Leave Category"
              value={category}
              onChange={(value) => value && handleCategoryChange(value as LeaveCategory)}
              data={Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }))}
            />
          </Group>

          <TextInput
            label="Start Date"
            type="date"
            value={formData.start_date || ""}
            onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
            required
          />

          <TextInput
            label="End Date"
            type="date"
            value={formData.end_date || ""}
            onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
            required
          />

          {showHalfDaySelect && (
            <Select
              label="Half Day"
              value={formData.half_day}
              onChange={(value) => setFormData({ ...formData, half_day: value as HalfDay })}
              data={[
                { value: "none", label: "Full day" },
                { value: "first", label: "First half" },
                { value: "second", label: "Second half" },
              ]}
            />
          )}

          <Textarea
            label="Purpose"
            value={formData.purpose || ""}
            onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
            placeholder="Briefly describe the reason for leave"
            required
          />

          <Checkbox
            label="I will leave the station"
            checked={formData.station_leave}
            onChange={(e) => setFormData({ ...formData, station_leave: e.currentTarget.checked })}
          />

          {formData.station_leave && (
            <Textarea
              label="Station Address"
              value={formData.station_address || ""}
              onChange={(e) => setFormData({ ...formData, station_address: e.target.value })}
              placeholder="Enter the address of the station you will be visiting"
            />
          )}

          <NumberInput
            label="Substitute (user id)"
            value={formData.substitute_id || ""}
            onChange={(value) => setFormData({ ...formData, substitute_id: String(value) })}
            placeholder="Enter user ID of the substitute"
          />

          <Button
            type="button"
            onClick={handleSubmit}
            loading={submitMutation.isPending}
            disabled={!formData.start_date || !formData.end_date || !formData.purpose}
          >
            Submit Application
          </Button>
        </Stack>
      </Card>
    </Container>
  );
}
