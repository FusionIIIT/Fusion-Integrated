import { useState, useEffect } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Loading, Select, Text, Textarea,
  notifications, useForm, FormProvider, useWatch, SchemaProvider,
} from "@mantine/core";
import { FaLeaf, FaCalendar, FaInfoCircle, FaTimesCircle } from "react-icons/fa";
import { useLeaveCategories, useLeaveBalances, useLeaveHistory,
         usePrintApplication, useYearEndProcessing } from "../api/hooks";
import { useNavigate } from "react-router-dom";
import type { LeaveCategory, LeaveBalance, LeaveHistoryEntry } from "../api/types";

/** EL-UC-001: Apply for Leave — Employee creates and submits a new leave application. */
export default function LeaveApplicationPage() {
  const navigate = useNavigate();

  // Fetch leave categories from API
  const categoriesQuery = useLeaveCategories();
  const balancesQuery = useLeaveBalances();
  const historyQuery = useLeaveHistory();

  const categories = categoriesQuery.data ?? [];
  const balances = balancesQuery.data?.balances ?? [];
  const history = historyQuery.data ?? [];

  // Form state
  const [formValues, setFormValues] = useState<LeaveApplicationCreateRequest>({
    leave_category_code: "",
    requested_start: "",
    requested_end: "",
    purpose_reason: "",
    station_leave: false,
    station_details: "",
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  // Derived: available categories based on employee type (faculty/staff)
  // and current balances
  const eligibleCategories = categories.filter((cat) => {
    // Check if employee has sufficient balance for the category
    const balance = balances.find((b) => b.leave_category_code === cat.code);
    if (!balance) return false;
    // For now, allow if balance is available (could be 0 for new entitlements)
    return balance.available_days >= 0;
  });

  // Handle form submission
  const onSubmit = async (values: LeaveApplicationCreateRequest) => {
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/v1/elm/apply", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to submit leave application");
      }

      const result: LeaveApplicationCreateResponse = await response.json();
      notifications.show({
        color: "green",
        title: "Leave application submitted",
        message: `Your ${result.message} has been submitted successfully.`,
      });

      // Reset form
      setFormValues({
        leave_category_code: "",
        requested_start: "",
        requested_end: "",
        purpose_reason: "",
        station_leave: false,
        station_details: "",
      });

      navigate("/elm/balances");
    } catch (e: any) {
      notifications.show({
        color: "red",
        title: "Could not submit leave application",
        message: e.message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Form validation helpers
  const validate = () => {
    const { leave_category_code, requested_start, requested_end } = formValues;
    if (!leave_category_code) {
      return "Please select a leave category";
    }
    if (!requested_start) {
      return "Please select a start date";
    }
    if (!requested_end) {
      return "Please select an end date";
    }
    const start = new Date(requested_start);
    const end = new Date(requested_end);
    if (end < start) {
      return "End date must be after start date";
    }
    return null;
  };

  // UI
  const error = validate();

  if (categoriesQuery.error) {
    return (
      <Container size="md">
        <ErrorState error={categoriesQuery.error} />
      </Container>
    );
  }

  if (!eligibleCategories.length) {
    return (
      <Container size="md">
        <PageHeader title="Apply for Leave" />
        <Alert variant="light" color="gray" icon={<FaInfoCircle />}>
          No leave categories are currently available for your employee type.
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="md">
      <PageHeader title="Apply for Leave" subtitle="Submit a new leave request" />

      {error && (
        <Alert variant="light" color="red" icon={<FaTimesCircle />}>
          <Text>{error}</Text>
        </Alert>
      )}

      <FormProvider>
        <SchemaProvider
          schema={({ getFieldState }) => ({
            fields: {
              leave_category_code: {
                validate: {
                  required: "Leave category is required",
                },
              },
              requested_start: {
                validate: {
                  required: "Start date is required",
                },
              },
              requested_end: {
                validate: {
                  required: "End date is required",
                },
              },
            },
          })}
        >
          <Card padding="lg">
            <Group gap="sm">
              {/* Leave Category Select */}
              <Select
                label="Leave Category"
                placeholder="Select leave category"
                data={eligibleCategories.map((cat) => ({
                  value: cat.code,
                  label: `${cat.code}: ${cat.label}`,
                }))}
                value={formValues.leave_category_code}
                onChange={(v) => setFormValues({ ...formValues, leave_category_code: v }) }
                disabled={isSubmitting}
              />

              {/* Requested Period */}
              <Group gap="sm">
                <Text>Requested Period</Text>
                <Select
                  label="Start Date"
                  placeholder="Select start date"
                  data={[
                    { value: "", label: "Select start date" },
                    ...Array.from({ length: 30 }, (_, i) => {
                      const d = new Date();
                      d.setDate(d.getDate() + i);
                      return { value: d.toISOString().split("T")[0], label: d.toLocaleDateString() };
                    }),
                  ]}
                  value={formValues.requested_start}
                  onChange={(v) => setFormValues({ ...formValues, requested_start: v }) }
                  disabled={isSubmitting}
                />
                <Select
                  label="End Date"
                  placeholder="Select end date"
                  data={[
                    { value: "", label: "Select end date" },
                    ...Array.from({ length: 30 }, (_, i) => {
                      const d = new Date();
                      d.setDate(d.getDate() + i);
                      return { value: d.toISOString().split("T")[0], label: d.toLocaleDateString() };
                    }),
                  ]}
                  value={formValues.requested_end}
                  onChange={(v) => setFormValues({ ...formValues, requested_end: v }) }
                  disabled={isSubmitting}
                />
              </Group>

              {/* Purpose/Reason */}
              <Group gap="sm">
                <Textarea
                  label="Purpose / Reason"
                  placeholder="Enter purpose or reason for leave"
                  rows={3}
                  value={formValues.purpose_reason}
                  onChange={(e) =>
                    setFormValues({ ...formValues, purpose_reason: e.target.value })}
                />
              </Group>

              {/* Station Leave */}
              <Group gap="sm">
                <Select
                  label="Station Leave"
                  placeholder="Will you be outside Jabalpur?"
                  value={formValues.station_leave ? "true" : "false"}
                  onChange={(v) =>
                    setFormValues({
                      ...formValues,
                      station_leave: v === "true",
                    })}
                >
                  <option value="false">No (in Jabalpur)</option>
                  <option value="true">Yes (outside Jabalpur)</option>
                </Select>

                {formValues.station_leave && (
                  <Textarea
                    label="Station Details"
                    placeholder="Details of absence outside Jabalpur"
                    rows={2}
                    value={formValues.station_details || ""}
                    onChange={(e) =>
                      setFormValues({
                        ...formValues,
                        station_details: e.target.value,
                      })}
                  />
                )}
              </Group>

              {/* Action buttons */}
              <Group gap="sm" justify="flex-end">
                <Button
                  variant="outline"
                  onClick={() => notifications.show({
                    color: "gray",
                    title: "Cancelled",
                    message: "Leave application was not submitted.",
                  })}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  loading={isSubmitting}
                  type="submit"
                  withinForm
                >
                  Submit Leave Application
                </Button>
              </Group>
            </Group>
          </Card>
        </SchemaProvider>
      </FormProvider>
    </Container>
  );
}

/** A simple ErrorState placeholder - in production this would be imported. */
function ErrorState({ error }: { error: any }) {
  return (
    <Card padding="lg" color="red">
      <Text fw={600} mb="xs">Error</Text>
      <Text c="red">{error || "Unknown error"}</Text>
    </Card>
  );
}