import { useState } from "react";
import {
  Button, Checkbox, Grid, NumberInput, Select, Stack, TextInput, Textarea,
} from "@mantine/core";

import type { LeaveRequestInput } from "../types";

const categories = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

export function LeaveRequestForm({
  onSubmit, loading,
}: {
  onSubmit: (input: LeaveRequestInput) => void;
  loading: boolean;
}) {
  const [category, setCategory] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState("none");
  const [purpose, setPurpose] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [destination, setDestination] = useState("");
  const [evidence, setEvidence] = useState("");
  const [substituteId, setSubstituteId] = useState<number | string>("");

  function submit() {
    if (!category || !startDate || !endDate || !purpose.trim()) return;
    onSubmit({
      category: category as LeaveRequestInput["category"],
      start_date: startDate,
      end_date: endDate,
      half_day: halfDay as LeaveRequestInput["half_day"],
      purpose: purpose.trim(),
      station_leave: stationLeave,
      station_destination: destination.trim(),
      medical_evidence_ref: evidence.trim(),
      ...(substituteId ? { substitute_user_id: Number(substituteId) } : {}),
    });
  }

  return (
    <Stack gap="sm">
      <Grid>
        <Grid.Col span={{ base: 12, sm: 6 }}>
          <Select
            label="Leave category" placeholder="Choose a category" required
            data={categories} value={category}
            onChange={(value) => {
              setCategory(value);
              if (value !== "CL") setHalfDay("none");
            }}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6 }}>
          <Select
            label="CL period" value={halfDay} onChange={(value) => setHalfDay(value ?? "none")}
            disabled={category !== "CL"} data={[
              { value: "none", label: "Full day" },
              { value: "first_half", label: "First half" },
              { value: "second_half", label: "Second half" },
            ]}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6 }}>
          <TextInput
            type="date" label="From" required value={startDate}
            onChange={(event) => setStartDate(event.currentTarget.value)}
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6 }}>
          <TextInput
            type="date" label="To" required value={endDate}
            onChange={(event) => setEndDate(event.currentTarget.value)}
          />
        </Grid.Col>
      </Grid>
      <Textarea
        label="Purpose / reason" required minRows={3} maxLength={2000}
        value={purpose} onChange={(event) => setPurpose(event.currentTarget.value)}
      />
      <Checkbox
        label="I will be outside Jabalpur (include Station Leave details)"
        checked={stationLeave} onChange={(event) => setStationLeave(event.currentTarget.checked)}
      />
      {stationLeave && (
        <TextInput
          label="Station Leave destination" required value={destination}
          onChange={(event) => setDestination(event.currentTarget.value)}
        />
      )}
      {category === "COL" && (
        <TextInput
          label="Medical evidence reference (if applicable)"
          value={evidence} onChange={(event) => setEvidence(event.currentTarget.value)}
          description="Enter the approved document reference; the policy may require supporting evidence."
        />
      )}
      <NumberInput
        label="Substitute employee ID (optional)" min={1}
        value={substituteId} onChange={setSubstituteId}
        description="The leave will wait for the nominated employee's consent."
      />
      <Button
        onClick={submit} loading={loading}
        disabled={!category || !startDate || !endDate || !purpose.trim()
          || (stationLeave && !destination.trim())}
      >
        Submit leave application
      </Button>
    </Stack>
  );
}