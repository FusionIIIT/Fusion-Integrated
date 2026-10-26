import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  Stack,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { errorMessage, http } from "../../../lib/http";

interface LeaveTypeItem {
  id: number;
  code: string;
  name: string;
}

export default function ApplyLeavePage() {
  const queryClient = useQueryClient();
  const [leaveType, setLeaveType] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [reason, setReason] = useState("");
  const [contactAddress, setContactAddress] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const typesQuery = useQuery({
    queryKey: ["elm", "types"],
    queryFn: async () => (await http.get<LeaveTypeItem[]>("/elm/types")).data,
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      return (
        await http.post("/elm/applications", {
          leave_type: Number(leaveType),
          start_date: startDate,
          end_date: endDate,
          is_half_day: isHalfDay,
          reason,
          contact_address: contactAddress,
        })
      ).data;
    },
    onSuccess: async () => {
      setErrorMsg("");
      setSuccessMsg("Leave application submitted.");
      setReason("");
      await queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
    onError: (err: unknown) => {
      setSuccessMsg("");
      setErrorMsg(errorMessage(err));
    },
  });

  const selectOptions = (typesQuery.data ?? []).map((t) => ({
    value: String(t.id),
    label: `${t.code} - ${t.name}`,
  }));

  return (
    <Container size="md" py="lg">
      <Stack gap="md">
        <Title order={2}>Apply Leave</Title>
        {errorMsg && <Alert color="red">{errorMsg}</Alert>}
        {successMsg && <Alert color="green">{successMsg}</Alert>}
        <Card withBorder>
          <Stack gap="sm">
            <Select
              label="Leave Type"
              placeholder="Select leave type"
              data={selectOptions}
              value={leaveType}
              onChange={setLeaveType}
            />
            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.currentTarget.value)}
              />
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.currentTarget.value)}
              />
            </Group>
            <Checkbox
              label="Half-day leave"
              checked={isHalfDay}
              onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
            />
            <Textarea
              label="Reason"
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
            />
            <TextInput
              label="Contact Address (optional)"
              value={contactAddress}
              onChange={(e) => setContactAddress(e.currentTarget.value)}
            />
            <Button
              loading={submitMutation.isPending}
              disabled={!leaveType || !startDate || !endDate || !reason}
              onClick={() => submitMutation.mutate()}
            >
              Submit Leave Request
            </Button>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
