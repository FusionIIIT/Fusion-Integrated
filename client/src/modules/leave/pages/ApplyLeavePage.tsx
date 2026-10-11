import { useState, useEffect } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Input, NumberInput, Select, Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useSubmitApplication } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

type LeaveCategory = "sick" | "personal" | "counseling" | "station";

export default function ApplyLeavePage() {
  const submitMutation = useSubmitApplication();
  const [formData, setFormData] = useState<Partial<LeaveApplication>>({
    leave_type: "sick",
    start_date: "",
    end_date: "",
    reason: "",
    unit_head_recommendation: "",
    final_sanction_decision: "",
  });

  const [category, setCategory] = useState<LeaveCategory>("sick");
  const [stationLeaveDetails, setStationLeaveDetails] = useState({
    is_station_leave: false,
    substitute_user_id: "",
  });

  useEffect(() => {
    if (category === "station") {
      setStationLeaveDetails((prev) => ({ ...prev, is_station_leave: true }));
    } else {
      setStationLeaveDetails((prev) => ({ ...prev, is_station_leave: false }));
    }
  }, [category]);

  function handleSubmit() {
    if (!formData.start_date || !formData.end_date || !formData.reason) {
      notifications.show({
        color: "red",
        title: "Missing Information",
        message: "Please fill in all required fields.",
      });
      return;
    }

    submitMutation.mutate(formData, {
      onSuccess: () => {
        notifications.show({
          color: "blue",
          title: "Application Submitted",
          message: "Your leave application has been submitted successfully.",
        });
      },
      onError: (e) => {
        notifications.show({
          color: "red",
          title: "Submission Failed",
          message: errorMessage(e),
        });
      },
    });
  }

  if (submitMutation.isPending) {
    return (
      <Container size="xl">
        <PageHeader title="Apply for Leave" subtitle="Submit a new leave request" />
        <Card padding="lg">
          <Text c="dimmed" size="sm">Submitting...</Text>
        </Card>
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="Apply for Leave" subtitle="Submit a new leave request" />
      <Card padding="lg">
        <Group mb="md">
          <Select
            label="Leave Category"
            value={category}
            onChange={(value) => setCategory(value as LeaveCategory)}
            data={[
              { value: "sick", label: "Sick Leave" },
              { value: "personal", label: "Personal Leave" },
              { value: "counseling", label: "Counseling Leave" },
              { value: "station", label: "Station Leave" },
            ]}
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

        <TextInput
          label="Reason"
          value={formData.reason || ""}
          onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
          placeholder="Briefly describe the reason for leave"
          required
        />

        {category === "station" && (
          <Card padding="sm" radius="md">
            <Text fw={600} mb="xs">Station Leave Details</Text>
            <Group mb="xs">
              <Input
                label="Substitute User ID"
                value={stationLeaveDetails.substitute_user_id || ""}
                onChange={(e) =>
                  setStationLeaveDetails({
                    ...stationLeaveDetails,
                    substitute_user_id: e.target.value,
                  })
                }
                placeholder="Enter user ID of the substitute"
              />
            </Group>
          </Card>
        )}

        <Button
          type="button"
          onClick={handleSubmit}
          leftIcon={<FaPlus />}
          loading={submitMutation.isPending}
        >
          Submit Application
        </Button>
      </Card>
    </Container>
  );
}
