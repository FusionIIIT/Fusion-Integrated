import { useState } from "react";
import { Button, Card, Container, Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecordOffline } from "../api/hooks";

export default function OfflinePage() {
  const record = useRecordOffline();
  const [userId, setUserId] = useState("");
  const [category, setCategory] = useState<string | null>("CL");
  const [startOn, setStartOn] = useState("");
  const [endOn, setEndOn] = useState("");
  const [purpose, setPurpose] = useState("");
  const [reference, setReference] = useState("");

  function save() {
    record.mutate({
      user_id: Number(userId), category, start_on: startOn, end_on: endOn,
      purpose, reference,
    }, {
      onSuccess: () => notifications.show({ color: "green", message: "Offline leave recorded" }),
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  return (
    <Container size="sm">
      <PageHeader title="Offline-sanctioned leave" subtitle="Record synchronization, not a second approval" />
      <Card padding="lg">
        <Stack>
          <TextInput label="Employee user id" value={userId} onChange={(e) => setUserId(e.target.value)} />
          <Select label="Category" value={category} onChange={setCategory}
            data={["CL", "RH", "SCL", "EL", "COL", "VL"]} />
          <TextInput type="date" label="Start" value={startOn} onChange={(e) => setStartOn(e.target.value)} />
          <TextInput type="date" label="End" value={endOn} onChange={(e) => setEndOn(e.target.value)} />
          <TextInput label="Purpose" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          <TextInput label="Sanction / reference evidence" value={reference}
            onChange={(e) => setReference(e.target.value)} />
          <Button onClick={save} loading={record.isPending}>Record</Button>
        </Stack>
      </Card>
    </Container>
  );
}
