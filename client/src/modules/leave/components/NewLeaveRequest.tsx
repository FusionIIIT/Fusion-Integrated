import { useState } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useAuth } from "../../../auth/AuthProvider";
import { http, errorMessage } from "../../../lib/http";
import { notifications } from "@mantine/notifications";
import { Button, Modal, TextInput, Select, Textarea, Checkbox, Group } from "@mantine/core";

export function NewLeaveRequest() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const [opened, setOpened] = useState(false);
  const [type, setType] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [dayPeriod, setDayPeriod] = useState<"full_day" | "first_half" | "second_half">("full_day");
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [stationContact, setStationContact] = useState("");
  const [substituteId, setSubstituteId] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      if (!type || !startDate || !endDate) throw new Error("Missing required fields");
      const payload: Record<string, any> = {
        leave_type: type,
        start_date: startDate,
        end_date: endDate,
        reason,
        day_period: dayPeriod,
      };
      if (isStationLeave) {
        payload.is_station_leave = true;
        payload.station_address = stationAddress;
        payload.station_contact = stationContact;
      }
      if (substituteId.trim()) {
        payload.substitute_id = substituteId.trim();
      }
      await http.post("/leave/requests/", payload);
    },
    onSuccess: () => {
      notifications.show({ title: "Success", message: "Leave request submitted" });
      setOpened(false);
      setType("CL");
      setStartDate(null);
      setEndDate(null);
      setReason("");
      setDayPeriod("full_day");
      setIsStationLeave(false);
      setStationAddress("");
      setStationContact("");
      setSubstituteId("");
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
    onError: (e) => {
      notifications.show({ title: "Error", message: errorMessage(e), color: "red" });
    },
  });

  if (!can("leave_cell.requests.manage")) return null;

  const handleSubmit = () => {
    mutation.mutate();
  };

  const isSubmitDisabled =
    !type ||
    !startDate ||
    !endDate ||
    (endDate && startDate && endDate < startDate) ||
    mutation.isPending;

  const handleTypeChange = (value: string | null) => {
    setType(value);
    if (value !== "CL") {
      setDayPeriod("full_day");
    }
  };

  const handleDayPeriodChange = (value: string | null) => {
    if (value === null) {
      setDayPeriod("full_day");
    } else {
      setDayPeriod(value as "full_day" | "first_half" | "second_half");
    }
  };

  return (
    <>
      <Button onClick={() => setOpened(true)}>New Leave Request</Button>
      <Modal opened={opened} onClose={() => setOpened(false)} title="New Leave Request">
        <Select
          label="Type"
          data={[
            { value: "CL", label: "Casual Leave" },
            { value: "RH", label: "Restricted Holiday" },
            { value: "SCL", label: "Special Casual Leave" },
            { value: "EL", label: "Earned Leave" },
            { value: "COL", label: "Commuted Leave" },
            { value: "VL", label: "Vacation Leave" },
          ]}
          value={type}
          onChange={handleTypeChange}
          required
        />
        {type === "CL" && (
          <Select
            label="Day Period"
            data={[
              { value: "full_day", label: "Full Day" },
              { value: "first_half", label: "First Half" },
              { value: "second_half", label: "Second Half" },
            ]}
            value={dayPeriod}
            onChange={handleDayPeriodChange}
            required
            mt="sm"
          />
        )}
        <TextInput
          label="Start Date"
          type="date"
          value={startDate ?? ""}
          onChange={(e) => setStartDate(e.currentTarget.value)}
          required
          mt="sm"
        />
        <TextInput
          label="End Date"
          type="date"
          value={endDate ?? ""}
          onChange={(e) => setEndDate(e.currentTarget.value)}
          required
          mt="sm"
        />
        <TextInput
          label="Proposed Substitute ID"
          placeholder="e.g. employee username"
          value={substituteId}
          onChange={(e) => setSubstituteId(e.currentTarget.value)}
          mt="sm"
        />
        <Textarea
          label="Reason"
          value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
          mt="sm"
        />
        <Checkbox
          label="Station Leave (leaving headquarters)"
          checked={isStationLeave}
          onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
          mt="md"
        />
        {isStationLeave && (
          <>
            <TextInput
              label="Station Address"
              placeholder="Address during station leave"
              value={stationAddress}
              onChange={(e) => setStationAddress(e.currentTarget.value)}
              mt="xs"
            />
            <TextInput
              label="Emergency Contact"
              placeholder="Contact phone/details"
              value={stationContact}
              onChange={(e) => setStationContact(e.currentTarget.value)}
              mt="xs"
            />
          </>
        )}
        <Group justify="flex-end" mt="md">
          <Button onClick={handleSubmit} fullWidth disabled={isSubmitDisabled} loading={mutation.isPending}>
            Submit
          </Button>
        </Group>
      </Modal>
    </>
  );
}
