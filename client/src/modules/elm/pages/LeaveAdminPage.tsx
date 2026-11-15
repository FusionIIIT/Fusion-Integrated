import {
  Alert, Button, Card, Group, NumberInput, Select, Stack, Text, TextInput,
  Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import {
  useLeavePolicies, useProcessYearEnd, useRecordOfflineLeave,
  useUpdateLeavePolicy,
} from "../api/hooks";
import LeaveAdminConfiguration from "./LeaveAdminConfiguration";

export default function LeaveAdminPage() {
  const { can } = useAuth();
  const [year, setYear] = useState<number | string>("");
  const process = useProcessYearEnd();
  const canManagePolicy = can("employee_leave.policy.manage");
  const policies = useLeavePolicies(canManagePolicy);
  const updatePolicy = useUpdateLeavePolicy();
  const recordOffline = useRecordOfflineLeave();
  const [policyYear, setPolicyYear] = useState<string | null>(null);
  const policy = policies.data?.results.find(
    (item) => String(item.year) === policyYear,
  );
  const [reminderHours, setReminderHours] = useState<number | string>("");
  const [escalateHours, setEscalateHours] = useState<number | string>("");
  const [escalationUserId, setEscalationUserId] = useState<number | string>("");
  const [applicantId, setApplicantId] = useState<number | string>("");
  const [category, setCategory] = useState<string | null>("CL");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [purpose, setPurpose] = useState("");
  const [sanctionReference, setSanctionReference] = useState("");
  const [offlineReason, setOfflineReason] = useState("");
  const [sanctionedOn, setSanctionedOn] = useState("");
  const completedYear = new Date().getFullYear() - 1;

  useEffect(() => {
    if (policy) {
      setReminderHours(policy.reminder_after_hours);
      setEscalateHours(policy.escalate_after_hours);
      setEscalationUserId(policy.escalation_user_id ?? "");
    }
  }, [policy]);

  const fail = (error: unknown) =>
    notifications.show({ color: "red", message: errorMessage(error) });

  const saveSla = () => {
    if (!policy || !Number(reminderHours) || !Number(escalateHours)
      || Number(escalateHours) <= Number(reminderHours)) {
      notifications.show({
        color: "red",
        message: "Escalation must be later than a positive reminder threshold.",
      });
      return;
    }
    updatePolicy.mutate({
      id: policy.id,
      reminder_after_hours: Number(reminderHours),
      escalate_after_hours: Number(escalateHours),
      escalation_user_id: escalationUserId ? Number(escalationUserId) : null,
    }, {
      onError: fail,
      onSuccess: () => notifications.show({ message: "SLA thresholds updated." }),
    });
  };

  const saveOfflineLeave = () => {
    if (!Number.isInteger(Number(applicantId)) || Number(applicantId) <= 0
      || !category || !startsOn || !endsOn || !purpose.trim()
      || !sanctionReference.trim() || !offlineReason.trim() || !sanctionedOn) {
      notifications.show({ color: "red", message: "Complete every offline leave field." });
      return;
    }
    recordOffline.mutate({
      applicant_user_id: Number(applicantId),
      category,
      starts_on: startsOn,
      ends_on: endsOn,
      purpose,
      offline_reference: sanctionReference,
      offline_reason: offlineReason,
      offline_sanctioned_on: sanctionedOn,
    }, {
      onError: fail,
      onSuccess: () => {
        setPurpose("");
        notifications.show({ message: "Sanctioned offline leave synchronized." });
      },
    });
  };

  return (
    <Stack>
      <Title order={2}>Leave Administration</Title>
      {canManagePolicy && (
        <Card withBorder>
          <Stack>
            <Title order={3}>Workflow SLA thresholds</Title>
            {policies.isError && (
              <Alert color="red" title="Unable to load leave policies">
                {errorMessage(policies.error)}
              </Alert>
            )}
            <Select
              label="Policy year"
              placeholder="Select a configured year"
              data={(policies.data?.results ?? []).map((item) => ({
                value: String(item.year), label: String(item.year),
              }))}
              value={policyYear}
              onChange={setPolicyYear}
            />
            {policy && (
              <>
                <Group grow>
                  <NumberInput
                    label="Reminder after hours"
                    min={1}
                    value={reminderHours}
                    onChange={setReminderHours}
                  />
                  <NumberInput
                    label="Escalate after hours"
                    min={1}
                    value={escalateHours}
                    onChange={setEscalateHours}
                  />
                </Group>
                <NumberInput
                  label="Escalation authority user ID (optional)"
                  description="If blank, notify the next configured workflow authority."
                  min={1}
                  value={escalationUserId}
                  onChange={setEscalationUserId}
                />
                <Button loading={updatePolicy.isPending} onClick={saveSla}>
                  Save SLA thresholds
                </Button>
              </>
            )}
          </Stack>
        </Card>
      )}
      {can("employee_leave.request.process") && (
        <Card withBorder>
          <Stack>
            <Title order={3}>Synchronize already-sanctioned offline leave</Title>
            <Text size="sm">
              This records a prior authorized sanction and updates its leave
              balance without starting another approval workflow.
            </Text>
            {recordOffline.data && (
              <Alert color="green" title="Offline leave synchronized">
                Request {recordOffline.data.id} was recorded as approved.
              </Alert>
            )}
            <NumberInput
              label="Employee user ID"
              min={1}
              value={applicantId}
              onChange={setApplicantId}
            />
            <Select
              label="Leave category"
              data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
              value={category}
              onChange={setCategory}
            />
            <Group grow>
              <TextInput
                label="Start date"
                type="date"
                value={startsOn}
                onChange={(event) => setStartsOn(event.currentTarget.value)}
              />
              <TextInput
                label="End date"
                type="date"
                value={endsOn}
                onChange={(event) => setEndsOn(event.currentTarget.value)}
              />
            </Group>
            <TextInput
              label="Purpose"
              value={purpose}
              onChange={(event) => setPurpose(event.currentTarget.value)}
            />
            <TextInput
              label="Sanction/reference number"
              value={sanctionReference}
              onChange={(event) => setSanctionReference(event.currentTarget.value)}
            />
            <TextInput
              label="Date sanctioned"
              type="date"
              value={sanctionedOn}
              onChange={(event) => setSanctionedOn(event.currentTarget.value)}
            />
            <Textarea
              label="Why ELM could not be used"
              value={offlineReason}
              onChange={(event) => setOfflineReason(event.currentTarget.value)}
            />
            <Button loading={recordOffline.isPending} onClick={saveOfflineLeave}>
              Synchronize offline sanction
            </Button>
          </Stack>
        </Card>
      )}
      {can("employee_leave.year_end.process") && (
        <Card withBorder>
          <Stack>
            <Text>Run year-end leave processing for a completed calendar year.</Text>
            {process.isError && (
              <Alert color="red" title="Year-end processing failed">
                {errorMessage(process.error)}
              </Alert>
            )}
            {process.data && (
              <Alert color="green" title="Year-end processing completed">
                {process.data.processed_accounts} accounts processed for {process.data.year}.
              </Alert>
            )}
            <NumberInput
              label="Completed leave year"
              min={1900}
              max={completedYear}
              value={year}
              onChange={setYear}
            />
            <Button
              disabled={!year || Number(year) > completedYear}
              loading={process.isPending}
              onClick={() => process.mutate(Number(year))}
            >
              Process year end
            </Button>
          </Stack>
        </Card>
      )}
      <LeaveAdminConfiguration />
    </Stack>
  );
}
