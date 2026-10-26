import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
  Container,
  Divider,
  Grid,
  Group,
  Loader,
  NumberInput,
  Paper,
  Radio,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheckCircle,
  FaExclamationCircle,
  FaFileAlt,
  FaLock,
  FaUserFriends,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateOfflineLeave,
  useLeaveTypes,
  useSearchDirectoryUsers,
} from "../api/hooks";
import type { DirectoryUser } from "../api/types";

export default function OfflineRecordsPage() {
  const { can, session } = useAuth();
  const canRecordOffline =
    can("leave.balance.update") ||
    (session?.roles ?? []).some((r) =>
      ["Leave Administrator", "hr_officer"].includes(r)
    );

  // Form states
  const [employeeUserId, setEmployeeUserId] = useState<number | string>("");
  const [leaveTypeCode, setLeaveTypeCode] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [reference, setReference] = useState("");
  const [sanctionedBy, setSanctionedBy] = useState("");
  const [sanctionedDate, setSanctionedDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState("forenoon");

  // User search helper
  const [userQuery, setUserQuery] = useState("");
  const [selectedEmployee, setSelectedEmployee] = useState<DirectoryUser | null>(
    null
  );

  const { data: leaveTypes, isPending: typesLoading, error: typesError } =
    useLeaveTypes();
  const { data: searchResults, isPending: searchLoading } =
    useSearchDirectoryUsers(userQuery);

  const createOffline = useCreateOfflineLeave();

  if (!canRecordOffline) {
    return (
      <Container size="md">
        <PageHeader
          title="Offline & Adjustment Records"
          subtitle="Administrative recording of offline-sanctioned leave."
        />
        <Alert
          color="red"
          icon={<FaLock />}
          title="Administrative Permission Required"
        >
          <Text size="sm">
            Only authorized Leave Administrators and HR Officers may record
            retrospective offline-sanctioned leave entries.
          </Text>
        </Alert>
      </Container>
    );
  }

  const selectedType = leaveTypes?.find((t) => t.code === leaveTypeCode);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const empId =
      selectedEmployee?.user_id ||
      (employeeUserId ? Number(employeeUserId) : null);

    if (!empId) {
      notifications.show({
        color: "red",
        title: "Employee ID Required",
        message: "Please specify the employee user ID.",
      });
      return;
    }

    if (!leaveTypeCode) {
      notifications.show({
        color: "red",
        title: "Leave Category Required",
        message: "Please select a leave category.",
      });
      return;
    }

    if (!startDate || !endDate) {
      notifications.show({
        color: "red",
        title: "Dates Required",
        message: "Start and end dates are required.",
      });
      return;
    }

    if (!reference.trim() || !sanctionedBy.trim() || !sanctionedDate) {
      notifications.show({
        color: "red",
        title: "Offline Reference Required",
        message: "Please enter the reference number, sanctioning authority, and order date.",
      });
      return;
    }

    createOffline.mutate(
      {
        employee_user_id: empId,
        leave_type_code: leaveTypeCode,
        start_date: startDate,
        end_date: endDate,
        reason: reason.trim(),
        offline_sanction_reference: reference.trim(),
        offline_sanctioned_by: sanctionedBy.trim(),
        offline_sanctioned_date: sanctionedDate,
        is_half_day: selectedType?.allows_half_day ? isHalfDay : false,
        half_day_period: isHalfDay ? halfDayPeriod : undefined,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "teal",
            title: "Offline Leave Recorded",
            message: `Recorded offline leave #${data.application_number} with reference "${data.offline_sanction_reference}".`,
          });
          // Reset form
          setReason("");
          setReference("");
          setSanctionedBy("");
          setSelectedEmployee(null);
          setEmployeeUserId("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Recording Error",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  if (typesError) {
    return (
      <Container size="md">
        <ErrorState error={typesError} />
      </Container>
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Record Offline Sanctioned Leave (BR-EL-029)"
        subtitle="Retrospectively synchronize leave already sanctioned via offline paper orders due to medical emergency, connectivity, or server outage."
      />

      <Card withBorder padding="xl" radius="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="lg">
            {createOffline.error && (
              <Alert
                color="red"
                icon={<FaExclamationCircle />}
                title="Failed to Record Offline Leave"
              >
                <Text size="sm">{errorMessage(createOffline.error)}</Text>
              </Alert>
            )}

            {/* Step 1: Employee Selection */}
            <FormSection
              title="1. Employee Identification"
              hint="Search or enter the institute member's user ID"
              first
            >
              <Stack gap="sm">
                <TextInput
                  label="Search Employee"
                  placeholder="Type colleague name or department..."
                  leftSection={<FaUserFriends />}
                  value={userQuery}
                  onChange={(e) => setUserQuery(e.currentTarget.value)}
                  rightSection={searchLoading ? <Loader size="xs" /> : null}
                />

                {searchResults && searchResults.length > 0 && (
                  <Paper withBorder p="xs" radius="sm">
                    <Text size="xs" fw={700} c="dimmed" mb="xs">
                      Matching Employees:
                    </Text>
                    <Stack gap="xs">
                      {searchResults.map((u) => (
                        <Group
                          key={u.user_id}
                          justify="space-between"
                          p="xs"
                          style={{
                            cursor: "pointer",
                            borderRadius: 4,
                            backgroundColor:
                              selectedEmployee?.user_id === u.user_id
                                ? "var(--mantine-color-blue-1)"
                                : "transparent",
                          }}
                          onClick={() => {
                            setSelectedEmployee(u);
                            setEmployeeUserId(u.user_id);
                          }}
                        >
                          <div>
                            <Text size="sm" fw={600}>
                              {u.display_name} ({u.username})
                            </Text>
                            <Text size="xs" c="dimmed">
                              User #{u.user_id} • {u.department}
                            </Text>
                          </div>
                          <Button size="compact-xs" variant="light">
                            Select
                          </Button>
                        </Group>
                      ))}
                    </Stack>
                  </Paper>
                )}

                {selectedEmployee ? (
                  <Alert
                    color="teal"
                    icon={<FaCheckCircle />}
                    title="Target Employee Selected"
                  >
                    <Text size="sm">
                      <strong>{selectedEmployee.display_name}</strong> (User ID:{" "}
                      {selectedEmployee.user_id}) — {selectedEmployee.department}
                    </Text>
                  </Alert>
                ) : (
                  <NumberInput
                    label="Or Enter Employee User ID directly"
                    placeholder="e.g. 1001"
                    required
                    value={employeeUserId}
                    onChange={(val) => setEmployeeUserId(val)}
                  />
                )}
              </Stack>
            </FormSection>

            <Divider />

            {/* Step 2: Leave Details */}
            <FormSection title="2. Leave Details">
              <Stack gap="sm">
                <Select
                  label="Leave Category"
                  placeholder="Select leave type..."
                  required
                  data={
                    leaveTypes?.map((t) => ({
                      value: t.code,
                      label: `${t.code} — ${t.name}`,
                    })) ?? []
                  }
                  value={leaveTypeCode}
                  onChange={(val) => {
                    setLeaveTypeCode(val);
                    setIsHalfDay(false);
                  }}
                  disabled={typesLoading}
                />

                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      type="date"
                      label="Start Date"
                      required
                      value={startDate}
                      onChange={(e) => {
                        setStartDate(e.currentTarget.value);
                        if (!endDate) setEndDate(e.currentTarget.value);
                      }}
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      type="date"
                      label="End Date"
                      required
                      min={startDate}
                      value={endDate}
                      onChange={(e) => setEndDate(e.currentTarget.value)}
                    />
                  </Grid.Col>
                </Grid>

                {selectedType?.allows_half_day && (
                  <Box mt="xs">
                    <Checkbox
                      label="Recorded as Half-Day Leave"
                      checked={isHalfDay}
                      onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
                    />
                    {isHalfDay && (
                      <Radio.Group
                        value={halfDayPeriod}
                        onChange={setHalfDayPeriod}
                        label="Half-Day Period"
                        mt="xs"
                      >
                        <Group mt="xs">
                          <Radio value="forenoon" label="Forenoon (FN)" />
                          <Radio value="afternoon" label="Afternoon (AN)" />
                        </Group>
                      </Radio.Group>
                    )}
                  </Box>
                )}

                <Textarea
                  label="Sanction Justification / Purpose"
                  placeholder="State the reason recorded in the offline order..."
                  required
                  minRows={2}
                  value={reason}
                  onChange={(e) => setReason(e.currentTarget.value)}
                />
              </Stack>
            </FormSection>

            <Divider />

            {/* Step 3: Offline Sanction Evidence */}
            <FormSection
              title="3. Offline Order / Reference Information"
              hint="Audit evidence of the offline decision (BR-EL-029)"
            >
              <Stack gap="sm">
                <TextInput
                  label="Sanction Order / File Reference Number"
                  placeholder="e.g. IIITDM/ESTT/LEAVE/2026/892"
                  required
                  leftSection={<FaFileAlt />}
                  value={reference}
                  onChange={(e) => setReference(e.currentTarget.value)}
                />

                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      label="Offline Sanctioning Authority"
                      placeholder="e.g. Director / Dean Academic"
                      required
                      value={sanctionedBy}
                      onChange={(e) => setSanctionedBy(e.currentTarget.value)}
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      type="date"
                      label="Order / Approval Date"
                      required
                      value={sanctionedDate}
                      onChange={(e) => setSanctionedDate(e.currentTarget.value)}
                    />
                  </Grid.Col>
                </Grid>
              </Stack>
            </FormSection>

            {/* Submission Actions */}
            <Group justify="flex-end" mt="xl">
              <Button
                type="submit"
                loading={createOffline.isPending}
                color="teal"
              >
                Record Offline Leave
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
