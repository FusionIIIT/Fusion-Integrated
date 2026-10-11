import { useState } from "react";
import {
  ActionIcon, Button, Card, Checkbox, Container, Group, Select, Stack, Text,
} from "@mantine/core";
import { DatePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaUserPlus, FaCheckCircle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { CpiBadge } from "../../placement/components/CpiBadge";
import { HistoryDrawer } from "../../placement/components/HistoryDrawer";
import { useApplications, useTransition } from "../api/hooks";
import type { Application } from "../api/types";

export default function LeaveRequestForm() {
  const [leaveType, setLeaveType] = useState("");
  const [startDate, setStartDate] = useState(new Date());
  const [endDate, setEndDate] = useState(new Date());
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [historyFor, setHistoryFor] = useState<number | null>(null);

  // BR-EL-012: Applicant non-overlap with half-day CL exception
  const isHalfDayCLOverlap = (startDate: Date, endDate: Date) => {
    const startHour = startDate.getHours();
    const endHour = endDate.getHours();

    if ((startHour >= 9 && startHour < 13) || (endHour > 12)) {
      return true;
    }

    return false;
  };

  // BR-EL-014: Substitute eligibility
  const [substitute, setSubstitute] = useState<number | null>(null);

  // BR-EL-015: Substitute consent gate and decline recovery
  const [substituteConsentAccepted, setSubstituteConsentAccepted] = useState(false);

  // BR-EL-016: Unit Head final scope for CL/RH
  const [unitHeadScopeFinal, setUnitHeadScopeFinal] = useState(true);

  // BR-EL-017: Unit Head recommendation for higher-sanction leave
  const [unitHeadRecommendationRecommended, setUnitHeadRecommendationRecommended] = useState(false);

  // BR-EL-018: Higher-sanction routing
  const [higherSanctionRouting, setHigherSanctionRouting] = useState(true);

  // BR-EL-023: Cancellation of approved leave before start
  const [cancelLeaveBeforeStart, setCancelLeaveBeforeStart] = useState(false);

  // BR-EL-025: Extension of ongoing EL/COL/VL
  const [extendLeave, setExtendLeave] = useState(false);

  const handleSubmit = async () => {
    if (!leaveType || !startDate || !endDate || !reason) {
      notifications.show({
        color: "red", title: "Incomplete form",
        message: "Please fill out all fields.",
      });
      return;
    }

    // BR-EL-012: Applicant non-overlap with half-day CL exception
    if (isHalfDayCLOverlap(startDate, endDate)) {
      notifications.show({
        color: "red", title: "Invalid date range",
        message: "Half-day Casual Leave cannot be scheduled during morning or afternoon.",
      });
      return;
    }

    // BR-EL-014: Substitute eligibility
    if (!substitute || !substituteConsentAccepted) {
      notifications.show({
        color: "red", title: "Invalid substitute",
        message: "Please select a valid substitute and confirm consent.",
      });
      return;
    }

    // BR-EL-016: Unit Head final scope for CL/RH
    if (!unitHeadScopeFinal) {
      notifications.show({
        color: "red", title: "Unit Head scope",
        message: "The Unit Head is not the final authority for this leave type.",
      });
      return;
    }

    // BR-EL-017: Unit Head recommendation for higher-sanction leave
    if (!unitHeadRecommendationRecommended) {
      notifications.show({
        color: "red", title: "Unit Head recommendation",
        message: "The Unit Head has not recommended this leave.",
      });
      return;
    }

    // BR-EL-018: Higher-sanction routing
    if (!higherSanctionRouting) {
      notifications.show({
        color: "red", title: "Higher sanction routing",
        message: "The leave cannot be routed to the higher sanctioning authority.",
      });
      return;
    }

    // BR-EL-023: Cancellation of approved leave before start
    if (cancelLeaveBeforeStart) {
      notifications.show({
        color: "red", title: "Cancellation before start",
        message: "The leave cannot be cancelled before it starts.",
      });
      return;
    }

    // BR-EL-025: Extension of ongoing EL/COL/VL
    if (extendLeave) {
      notifications.show({
        color: "red", title: "Extension",
        message: "The leave cannot be extended while it is ongoing.",
      });
      return;
    }

    setSubmitting(true);

    try {
      // Simulate API call to submit the leave request
      await new Promise((resolve) => setTimeout(resolve, 1000));

      notifications.show({
        color: "green", title: "Leave submitted",
        message: `Your leave request for ${leaveType} from ${startDate.toLocaleDateString()} to ${endDate.toLocaleDateString()} has been submitted.`,
      });
    } catch (e) {
      notifications.show({
        color: "red", title: "Could not submit leave",
        message: errorMessage(e),
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Submit Leave Request"
        subtitle="Fill out the form to apply for a leave"
      />
      <Card padding="lg">
        <Stack gap={20}>
          {/* BR-EL-014: Substitute eligibility */}
          <Group>
            <Text fw={600}>Substitute</Text>
            <Select
              value={substitute}
              onChange={(value) => setSubstitute(Number(value))}
              data={[
                { label: "Select a substitute", value: null },
                // Populate with actual substitutes from the database
              ]}
              placeholder="Select a substitute"
              required
            />
          </Group>

          {/* BR-EL-015: Substitute consent gate and decline recovery */}
          <Group>
            <Text fw={600}>Substitute Consent</Text>
            <Checkbox
              checked={substituteConsentAccepted}
              onChange={(value) => setSubstituteConsentAccepted(value)}
              label="I agree to accept the substitute's consent"
            />
          </Group>

          {/* BR-EL-012: Applicant non-overlap with half-day CL exception */}
          <Group>
            <Text fw={600}>Half-Day Casual Leave</Text>
            <Checkbox
              checked={isHalfDayCLOverlap(startDate, endDate)}
              onChange={(value) => setIsHalfDayCLOverlap(value)}
              label="This leave request overlaps with a Half-Day Casual Leave"
            />
          </Group>

          {/* BR-EL-016: Unit Head final scope for CL/RH */}
          <Group>
            <Text fw={600}>Unit Head Scope</Text>
            <Checkbox
              checked={unitHeadScopeFinal}
              onChange={(value) => setUnitHeadScopeFinal(value)}
              label="The Unit Head is the final authority for this leave type"
            />
          </Group>

          {/* BR-EL-017: Unit Head recommendation for higher-sanction leave */}
          <Group>
            <Text fw={600}>Unit Head Recommendation</Text>
            <Checkbox
              checked={unitHeadRecommendationRecommended}
              onChange={(value) => setUnitHeadRecommendationRecommended(value)}
              label="The Unit Head has recommended this leave"
            />
          </Group>

          {/* BR-EL-018: Higher-sanction routing */}
          <Group>
            <Text fw={600}>Higher Sanction Routing</Text>
            <Checkbox
              checked={higherSanctionRouting}
              onChange={(value) => setHigherSanctionRouting(value)}
              label="The leave can be routed to the higher sanctioning authority"
            />
          </Group>

          {/* BR-EL-023: Cancellation of approved leave before start */}
          <Group>
            <Text fw={600}>Cancellation Before Start</Text>
            <Checkbox
              checked={cancelLeaveBeforeStart}
              onChange={(value) => setCancelLeaveBeforeStart(value)}
              label="The leave cannot be cancelled before it starts"
            />
          </Group>

          {/* BR-EL-025: Extension of ongoing EL/COL/VL */}
          <Group>
            <Text fw={600}>Extension</Text>
            <Checkbox
              checked={extendLeave}
              onChange={(value) => setExtendLeave(value)}
              label="The leave cannot be extended while it is ongoing"
            />
          </Group>

          {/* Leave Type */}
          <Select
            value={leaveType}
            onChange={(value) => setLeaveType(value)}
            data={[
              { label: "Casual Leave", value: "CL" },
              { label: "Restricted Holiday", value: "RH" },
              // Add other leave types as needed
            ]}
            placeholder="Select a leave type"
            required
          />

          {/* Start Date */}
          <DatePicker
            value={startDate}
            onChange={(value) => setStartDate(value)}
            label="Start Date"
            required
          />

          {/* End Date */}
          <DatePicker
            value={endDate}
            onChange={(value) => setEndDate(value)}
            label="End Date"
            required
          />

          {/* Reason */}
          <Textarea
            value={reason}
            onChange={(value) => setReason(value)}
            label="Reason"
            placeholder="Enter the reason for your leave"
            required
          />

          {/* Submit Button */}
          <Button variant="primary" onClick={handleSubmit} loading={submitting}>
            {submitting ? "Submitting..." : "Submit Leave Request"}
          </Button>
        </Stack>
      </Card>

      <HistoryDrawer
        applicationId={historyFor} onClose={() => setHistoryFor(null)}
      />
    </Container>
  );
}
