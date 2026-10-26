import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Alert,
  Badge,
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
  ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaArrowLeft,
  FaCalendarCheck,
  FaExclamationCircle,
  FaInfoCircle,
  FaPlaneDeparture,
  FaUserFriends,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useApplyLeave,
  useLeaveBalances,
  useLeaveTypes,
  useSearchDirectoryUsers,
} from "../api/hooks";
import type { DirectoryUser } from "../api/types";

export default function ApplyPage() {
  const navigate = useNavigate();

  // Form states
  const [leaveTypeCode, setLeaveTypeCode] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState("forenoon");

  // Station leave states
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationDestination, setStationDestination] = useState("");
  const [stationDepartureDate, setStationDepartureDate] = useState("");
  const [stationArrivalDate, setStationArrivalDate] = useState("");

  // Contact & Address
  const [addressDuringLeave, setAddressDuringLeave] = useState("");
  const [contactNumber, setContactNumber] = useState("");

  // Substitute nomination
  const [substituteSearchQuery, setSubstituteSearchQuery] = useState("");
  const [selectedSubstitute, setSelectedSubstitute] = useState<DirectoryUser | null>(null);
  const [manualSubstituteId, setManualSubstituteId] = useState<number | string>("");

  const { data: leaveTypes, isPending: typesLoading, error: typesError } = useLeaveTypes();
  const { data: balances } = useLeaveBalances();
  const { data: searchResults, isPending: searchLoading } = useSearchDirectoryUsers(substituteSearchQuery);

  const applyMutation = useApplyLeave();

  const selectedType = leaveTypes?.find((t) => t.code === leaveTypeCode);
  const selectedBalance = balances?.find((b) => b.leave_type?.code === leaveTypeCode);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!leaveTypeCode) {
      notifications.show({ color: "red", title: "Select Leave Type", message: "Please select a leave category." });
      return;
    }

    if (!startDate || !endDate) {
      notifications.show({ color: "red", title: "Dates Required", message: "Start and end dates are required." });
      return;
    }

    if (!reason.trim()) {
      notifications.show({ color: "red", title: "Reason Required", message: "Please provide a reason for the leave." });
      return;
    }

    const substituteId = selectedSubstitute?.user_id || (manualSubstituteId ? Number(manualSubstituteId) : null);
    if (selectedType?.requires_substitute && !substituteId) {
      notifications.show({
        color: "red",
        title: "Substitute Required",
        message: `${selectedType.name} requires an active substitute nomination.`,
      });
      return;
    }

    if (isStationLeave && !stationDestination.trim()) {
      notifications.show({
        color: "red",
        title: "Station Destination Required",
        message: "Please specify the station destination.",
      });
      return;
    }

    applyMutation.mutate(
      {
        leave_type_code: leaveTypeCode,
        start_date: startDate,
        end_date: endDate,
        reason: reason.trim(),
        is_half_day: selectedType?.allows_half_day ? isHalfDay : false,
        half_day_period: isHalfDay ? halfDayPeriod : undefined,
        is_station_leave: isStationLeave,
        station_destination: isStationLeave ? stationDestination.trim() : undefined,
        station_departure_date: isStationLeave ? stationDepartureDate || null : null,
        station_arrival_date: isStationLeave ? stationArrivalDate || null : null,
        substitute_user_id: substituteId,
        address_during_leave: addressDuringLeave.trim() || undefined,
        contact_number: contactNumber.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "green",
            title: "Application Submitted",
            message: `Leave application #${data.application_number} submitted successfully.`,
          });
          navigate("/leave/mine");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Application Error",
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
        title="Apply for Leave"
        subtitle="Submit a new leave application according to institute policy rules."
        action={
          <Button component={Link} to="/leave/mine" variant="subtle" leftSection={<FaArrowLeft />}>
            Back to My Leaves
          </Button>
        }
      />

      <Card withBorder padding="xl" radius="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="lg">
            {applyMutation.error && (
              <Alert color="red" icon={<FaExclamationCircle />} title="Unable to Submit Application">
                <Text size="sm">{errorMessage(applyMutation.error)}</Text>
              </Alert>
            )}

            {/* Step 1: Leave Category & Details */}
            <FormSection title="1. Leave Category & Policy" first>
              <Stack gap="sm">
                <Select
                  label="Select Leave Type"
                  placeholder={typesLoading ? "Loading leave types..." : "Choose leave category..."}
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

                {selectedType && (
                  <Paper withBorder p="sm" bg="var(--mantine-color-blue-0)">
                    <Group justify="space-between" mb="xs">
                      <Group gap="xs">
                        <ThemeIcon size="sm" color="blue">
                          <FaInfoCircle />
                        </ThemeIcon>
                        <Text fw={600} size="sm">
                          {selectedType.name} ({selectedType.code})
                        </Text>
                      </Group>
                      {selectedBalance && (
                        <Badge color="blue" variant="filled">
                          Available: {selectedBalance.available_days} days
                        </Badge>
                      )}
                    </Group>
                    <Group gap="xs">
                      <Badge size="xs" variant="outline" color={selectedType.allows_half_day ? "green" : "gray"}>
                        {selectedType.allows_half_day ? "Half-Day Allowed" : "No Half-Day"}
                      </Badge>
                      <Badge size="xs" variant="outline" color={selectedType.requires_substitute ? "orange" : "gray"}>
                        {selectedType.requires_substitute ? "Requires Substitute" : "No Substitute Needed"}
                      </Badge>
                      <Badge size="xs" variant="outline" color={selectedType.is_continuous_count ? "indigo" : "gray"}>
                        {selectedType.is_continuous_count ? "Calendar/Continuous Count" : "Working Day Count"}
                      </Badge>
                      {selectedType.requires_medical_certificate && (
                        <Badge size="xs" variant="outline" color="red">
                          Medical Certificate Required
                        </Badge>
                      )}
                    </Group>
                  </Paper>
                )}
              </Stack>
            </FormSection>

            <Divider />

            {/* Step 2: Dates and Duration */}
            <FormSection title="2. Dates & Duration">
              <Stack gap="sm">
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
                      label="Apply for Half-Day Leave"
                      checked={isHalfDay}
                      onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
                    />
                    {isHalfDay && (
                      <Radio.Group
                        value={halfDayPeriod}
                        onChange={setHalfDayPeriod}
                        label="Half-Day Session"
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
                  label="Reason for Leave"
                  placeholder="State the purpose of your leave..."
                  required
                  minRows={3}
                  value={reason}
                  onChange={(e) => setReason(e.currentTarget.value)}
                />
              </Stack>
            </FormSection>

            {/* Step 3: Substitute Nomination (if applicable) */}
            {selectedType?.requires_substitute && (
              <>
                <Divider />
                <FormSection
                  title="3. Substitute Nomination"
                  hint="Nominate an eligible colleague to take over your academic and administrative responsibilities."
                >
                  <Stack gap="sm">
                    <TextInput
                      label="Search Colleague by Name or Department"
                      placeholder="Type at least 2 characters to search..."
                      leftSection={<FaUserFriends />}
                      value={substituteSearchQuery}
                      onChange={(e) => setSubstituteSearchQuery(e.currentTarget.value)}
                      rightSection={searchLoading ? <Loader size="xs" /> : null}
                    />

                    {searchResults && searchResults.length > 0 && (
                      <Paper withBorder p="xs" radius="sm">
                        <Text size="xs" fw={700} c="dimmed" mb="xs">
                          Search Results (click to select):
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
                                  selectedSubstitute?.user_id === u.user_id
                                    ? "var(--mantine-color-blue-1)"
                                    : "transparent",
                              }}
                              onClick={() => {
                                setSelectedSubstitute(u);
                                setManualSubstituteId(u.user_id);
                              }}
                            >
                              <div>
                                <Text size="sm" fw={600}>
                                  {u.display_name} ({u.username})
                                </Text>
                                <Text size="xs" c="dimmed">
                                  {u.department || u.kind || "Institute Member"}
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

                    {selectedSubstitute ? (
                      <Alert color="teal" icon={<FaCalendarCheck />} title="Selected Substitute">
                        <Text size="sm">
                          <strong>{selectedSubstitute.display_name}</strong> (User ID: {selectedSubstitute.user_id}) —{" "}
                          {selectedSubstitute.department}
                        </Text>
                      </Alert>
                    ) : (
                      <NumberInput
                        label="Or enter Substitute Employee User ID directly"
                        placeholder="e.g. 1002"
                        value={manualSubstituteId}
                        onChange={(val) => setManualSubstituteId(val)}
                      />
                    )}
                  </Stack>
                </FormSection>
              </>
            )}

            <Divider />

            {/* Step 4: Station Leave & Contact */}
            <FormSection title="4. Station Leave & Contact Details">
              <Stack gap="sm">
                <Checkbox
                  label="Station Leave (Leaving Headquarters)"
                  checked={isStationLeave}
                  onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
                />

                {isStationLeave && (
                  <Paper withBorder p="md" bg="var(--mantine-color-gray-0)">
                    <Stack gap="sm">
                      <TextInput
                        label="Station Destination"
                        placeholder="Destination city, venue, or address..."
                        required
                        leftSection={<FaPlaneDeparture />}
                        value={stationDestination}
                        onChange={(e) => setStationDestination(e.currentTarget.value)}
                      />
                      <Grid>
                        <Grid.Col span={{ base: 12, sm: 6 }}>
                          <TextInput
                            type="date"
                            label="Departure Date from Headquarters"
                            value={stationDepartureDate}
                            onChange={(e) => setStationDepartureDate(e.currentTarget.value)}
                          />
                        </Grid.Col>
                        <Grid.Col span={{ base: 12, sm: 6 }}>
                          <TextInput
                            type="date"
                            label="Expected Arrival Date back to Headquarters"
                            value={stationArrivalDate}
                            onChange={(e) => setStationArrivalDate(e.currentTarget.value)}
                          />
                        </Grid.Col>
                      </Grid>
                    </Stack>
                  </Paper>
                )}

                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      label="Contact Number During Leave"
                      placeholder="e.g. +91 98765 43210"
                      value={contactNumber}
                      onChange={(e) => setContactNumber(e.currentTarget.value)}
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6 }}>
                    <TextInput
                      label="Address During Leave"
                      placeholder="Temporary address..."
                      value={addressDuringLeave}
                      onChange={(e) => setAddressDuringLeave(e.currentTarget.value)}
                    />
                  </Grid.Col>
                </Grid>
              </Stack>
            </FormSection>

            {/* Submission Actions */}
            <Group justify="flex-end" mt="xl">
              <Button component={Link} to="/leave/mine" variant="default" disabled={applyMutation.isPending}>
                Cancel
              </Button>
              <Button type="submit" loading={applyMutation.isPending} color="blue">
                Submit Leave Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
