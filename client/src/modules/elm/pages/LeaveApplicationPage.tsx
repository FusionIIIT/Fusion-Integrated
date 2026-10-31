import { useState, type FormEvent } from "react";
import {
  Alert, Button, Card, Checkbox, Container, Select, Stack, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import {
  useLeaveBalances, useLeaveCategories, useSubmitLeaveApplication,
} from "../api/hooks";
import type { LeaveApplicationCreateRequest } from "../api/types";

const EMPTY_FORM: LeaveApplicationCreateRequest = {
  leave_category_code: "",
  requested_start: "",
  requested_end: "",
  day_part: "full_day",
  purpose_reason: "",
  station_leave: false,
  station_details: "",
};

export default function LeaveApplicationPage() {
  const categoriesQuery = useLeaveCategories();
  const balancesQuery = useLeaveBalances();
  const submit = useSubmitLeaveApplication();
  const [values, setValues] = useState(EMPTY_FORM);

  if (categoriesQuery.error) {
    return <Container size="md"><ErrorState error={categoriesQuery.error} /></Container>;
  }
  if (balancesQuery.error) {
    return <Container size="md"><ErrorState error={balancesQuery.error} /></Container>;
  }

  const categories = categoriesQuery.data ?? [];
  const balances = balancesQuery.data?.balances ?? [];
  const availableCodes = new Set(
    balances.filter((balance) => balance.available_days > 0)
      .map((balance) => balance.leave_category_code),
  );
  const selectedCategory = categories.find(
    (category) => category.code === values.leave_category_code,
  );
  const categoryOptions = categories
    .filter((category) => availableCodes.has(category.code))
    .map((category) => ({
      value: category.code,
      label: category.code + " — " + category.label,
    }));

  function onChange<K extends keyof LeaveApplicationCreateRequest>(
    key: K,
    value: LeaveApplicationCreateRequest[K],
  ) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!values.leave_category_code || !values.requested_start
      || !values.requested_end || !values.purpose_reason.trim()) {
      notifications.show({
        color: "orange",
        title: "Complete the required fields",
        message: "Choose a leave category, dates, and a reason.",
      });
      return;
    }
    if (values.day_part !== "full_day" && values.requested_start !== values.requested_end) {
      notifications.show({
        color: "orange",
        title: "Half-day CL must use one date",
        message: "Choose the same start and end date for a half-day request.",
      });
      return;
    }
    if (values.requested_end < values.requested_start) {
      notifications.show({
        color: "orange",
        title: "Check the leave period",
        message: "The end date must be on or after the start date.",
      });
      return;
    }

    submit.mutate(values, {
      onSuccess: (result) => {
        notifications.show({
          color: "green",
          title: "Leave application submitted",
          message: result.message + " was sent for Unit Head review.",
        });
        setValues(EMPTY_FORM);
      },
      onError: (error) => notifications.show({
        color: "red",
        title: "Could not submit the application",
        message: errorMessage(error),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit one request for leave and any associated Station Leave details"
      />
      {categoryOptions.length === 0 ? (
        <Alert color="gray">
          No applicable leave category has an available balance.
        </Alert>
      ) : (
        <Card withBorder>
          <form onSubmit={onSubmit}>
            <Stack>
              <Select
                label="Leave category"
                placeholder="Select a category"
                data={categoryOptions}
                value={values.leave_category_code || null}
                onChange={(value) => {
                  onChange("leave_category_code", value ?? "");
                  if (value !== "CL") onChange("day_part", "full_day");
                }}
                required
              />
              {selectedCategory?.supports_half_day && (
                <Select
                  label="CL day part"
                  data={[
                    { value: "full_day", label: "Full day" },
                    { value: "first_half", label: "First half (0.5 day)" },
                    { value: "second_half", label: "Second half (0.5 day)" },
                  ]}
                  value={values.day_part}
                  onChange={(value) => {
                    if (value) onChange("day_part", value as LeaveApplicationCreateRequest["day_part"]);
                  }}
                />
              )}
              <TextInput
                type="date"
                label="Start date"
                value={values.requested_start}
                onChange={(event) => onChange("requested_start", event.currentTarget.value)}
                required
              />
              <TextInput
                type="date"
                label="End date"
                value={values.requested_end}
                onChange={(event) => onChange("requested_end", event.currentTarget.value)}
                required
              />
              <Textarea
                label="Purpose / reason"
                value={values.purpose_reason}
                onChange={(event) => onChange("purpose_reason", event.currentTarget.value)}
                minRows={3}
                required
              />
              <Checkbox
                label="I will be outside Jabalpur during this leave"
                checked={values.station_leave}
                onChange={(event) => onChange("station_leave", event.currentTarget.checked)}
              />
              {values.station_leave && (
                <Textarea
                  label="Station Leave details"
                  value={values.station_details ?? ""}
                  onChange={(event) => onChange("station_details", event.currentTarget.value)}
                  required
                />
              )}
              <Button type="submit" loading={submit.isPending}>
                Submit application
              </Button>
            </Stack>
          </form>
        </Card>
      )}
    </Container>
  );
}
