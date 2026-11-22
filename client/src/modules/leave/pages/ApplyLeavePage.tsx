import { useState } from "react";
import {
  Alert, Button, Checkbox, Container, NumberInput, Select, Stack, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateApplication, leaveTypes } from "../api/hooks";

export default function ApplyLeavePage() {
  const create = useCreateApplication();
  const [leaveType, setLeaveType] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [half, setHalf] = useState<string | null>("");
  const [purpose, setPurpose] = useState("");
  const [station, setStation] = useState(false);
  const [stationDetails, setStationDetails] = useState("");
  const [substituteId, setSubstituteId] = useState<number | string>("");
  const [evidence, setEvidence] = useState("");

  function submit() {
    create.mutate({
      leave_type: leaveType,
      start_date: startDate,
      end_date: endDate,
      half_day_period: half,
      purpose,
      station_leave: station,
      station_leave_details: stationDetails,
      substitute_user_id: substituteId === "" ? null : Number(substituteId),
      medical_evidence_reference: evidence,
    }, {
      onSuccess: () => {
        notifications.show({ title: "Leave request submitted", message: "Your request is in the configured processing path." });
        setPurpose("");
      },
      onError: (error) => notifications.show({ color: "red", title: "Could not submit", message: errorMessage(error) }),
    });
  }

  return (
    <Container size="md">
      <PageHeader title="Apply for Leave" subtitle="Submit a leave request for processing." />
      {create.error && <ErrorState error={create.error} />}
      <Stack gap="md">
        <Select label="Leave category" data={leaveTypes()} value={leaveType}
          onChange={setLeaveType} required />
        <TextInput label="Start date" type="date" value={startDate}
          onChange={(event) => setStartDate(event.currentTarget.value)} required />
        <TextInput label="End date" type="date" value={endDate}
          onChange={(event) => setEndDate(event.currentTarget.value)} required />
        {leaveType === "CL" && startDate === endDate && (
          <Select label="Half day (optional)" data={[
            { value: "first", label: "First half" }, { value: "second", label: "Second half" },
          ]} clearable value={half} onChange={setHalf} />
        )}
        <Textarea label="Purpose / reason" value={purpose}
          onChange={(event) => setPurpose(event.currentTarget.value)} required />
        <NumberInput label="Substitute employee ID (if required by policy)"
          value={substituteId} onChange={setSubstituteId} min={1} />
        <TextInput label="Medical evidence reference (if required by policy)"
          value={evidence} onChange={(event) => setEvidence(event.currentTarget.value)} />
        <Checkbox label="I will be outside Jabalpur (Station Leave)" checked={station}
          onChange={(event) => setStation(event.currentTarget.checked)} />
        {station && <Textarea label="Station Leave details" value={stationDetails}
          onChange={(event) => setStationDetails(event.currentTarget.value)} required />}
        {leaveType === "VL" && <Alert color="blue" variant="light">
          Vacation-period validation requires the configured Academic Calendar provider.
        </Alert>}
        <Button onClick={submit} loading={create.isPending}
          disabled={!leaveType || !startDate || !endDate || !purpose.trim()}>
          Submit application
        </Button>
      </Stack>
    </Container>
  );
}
