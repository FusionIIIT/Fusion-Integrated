import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Container, NumberInput, Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type Submission = {
  leave_type_code: string;
  requested_start_date: string;
  requested_end_date: string;
  substitute_user_id: number;
  day_part: string;
};

export default function SubmitLeavePage() {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [leaveType, setLeaveType] = useState<string | null>("CL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [dayPart, setDayPart] = useState<string | null>("FULL");
  const [substitute, setSubstitute] = useState<number | string>("");

  const submit = useMutation({
    mutationFn: async (payload: Submission) =>
      (await http.post("/leave/requests/submit", payload)).data,
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["elm"] });
      notifications.show({ title: "Request submitted", message: "Your request is waiting for the nominated substitute.", color: "green" });
      navigate("/leave/my");
    },
  });

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!leaveType || !start || !end || !substitute) return;
    submit.mutate({
      leave_type_code: leaveType,
      requested_start_date: start,
      requested_end_date: end,
      substitute_user_id: Number(substitute),
      day_part: dayPart ?? "FULL",
    });
  }

  return (
    <Container size="md">
      <PageHeader title="Request leave" subtitle="Submit a leave request and nominate an eligible substitute" />
      <form onSubmit={onSubmit}>
        <Stack>
          {submit.error && <Alert color="red" title="Could not submit request">{errorMessage(submit.error)}</Alert>}
          <Select label="Leave type" required value={leaveType} onChange={setLeaveType} data={[
            { value: "CL", label: "Casual Leave" }, { value: "RH", label: "Restricted Holiday" },
            { value: "SCL", label: "Special Casual Leave" }, { value: "EL", label: "Earned Leave" },
            { value: "COL", label: "Commuted Leave" }, { value: "VL", label: "Vacation Leave" },
          ]} />
          <TextInput label="Start date" type="date" required value={start} onChange={(event) => setStart(event.currentTarget.value)} />
          <TextInput label="End date" type="date" required value={end} onChange={(event) => setEnd(event.currentTarget.value)} />
          {leaveType === "CL" && (
            <Select label="Day part" value={dayPart} onChange={setDayPart} data={[
              { value: "FULL", label: "Full day" }, { value: "FIRST_HALF", label: "First half" },
              { value: "SECOND_HALF", label: "Second half" },
            ]} />
          )}
          <NumberInput label="Substitute employee user ID" description="Use the Fusion employee user ID" required min={1} value={substitute} onChange={setSubstitute} />
          <Button type="submit" loading={submit.isPending}>Submit request</Button>
        </Stack>
      </form>
    </Container>
  );
}
