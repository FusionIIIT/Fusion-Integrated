import { useState } from "react";
import { Button, Container, Paper, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useCreateResumption, useResumptions } from "../api/hooks";

export default function ResumptionsPage() {
  const applications = useApplications();
  const resumptions = useResumptions();
  const create = useCreateResumption();
  const [applicationId, setApplicationId] = useState<number | string>("");
  const [actualDate, setActualDate] = useState("");
  const eligible = (applications.data ?? []).filter((row) =>
    ["EL", "COL", "VL"].includes(row.leave_type) && row.status === "approved");
  const error = applications.error ?? resumptions.error;

  return <Container size="lg">
    <PageHeader title="Resumption of Duty" subtitle="Record the actual return date for approved EL, COL, or VL." />
    {error && <ErrorState error={error} />}
    <Paper withBorder p="md" mb="lg">
      <Stack>
        <TextInput label="Approved application ID" type="number" value={applicationId}
          onChange={(event) => setApplicationId(event.currentTarget.value)} />
        {eligible.map((row) => <Text key={row.id} size="sm">
          Request {row.id}: {row.leave_type}, {row.start_date} – {row.end_date}
        </Text>)}
        <TextInput label="Actual resumption date" type="date" value={actualDate}
          onChange={(event) => setActualDate(event.currentTarget.value)} />
        <Button loading={create.isPending} disabled={!applicationId || !actualDate}
          onClick={() => create.mutate({ application_id: Number(applicationId), actual_resumption_date: actualDate }, {
            onSuccess: () => notifications.show({ title: "Resumption recorded", message: "It is awaiting review." }),
            onError: (reason) => notifications.show({ color: "red", title: "Could not record resumption", message: errorMessage(reason) }),
          })}>Submit resumption</Button>
      </Stack>
    </Paper>
    <Stack>
      {(resumptions.data ?? []).map((row) => <Paper key={row.id} withBorder p="md">
        <Text>Request {row.application_id} · returned {row.actual_resumption_date} · {row.state}</Text>
      </Paper>)}
    </Stack>
  </Container>;
}
