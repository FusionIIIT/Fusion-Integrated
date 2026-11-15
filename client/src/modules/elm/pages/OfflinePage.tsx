import {
  Button, Card, Container, Group, Select, SimpleGrid, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useOfflineRecords, useRecordOffline } from "../api/hooks";
import { CATEGORY_LABELS, type Category, type OfflineInput } from "../api/types";
import { EmployeePicker } from "../components/EmployeePicker";

const EMPTY: Omit<OfflineInput, "user_id"> & { user_id: number | null } = {
  user_id: null, category: "CL", start_date: "", end_date: "", half: "", purpose: "",
  sanction_reference: "", sanctioned_by: "", sanctioned_on: "", evidence_note: "",
};

export default function OfflinePage() {
  const { data, isPending, error } = useOfflineRecords();
  const record = useRecordOffline();
  const [v, setV] = useState(EMPTY);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  const ready = v.user_id != null && v.start_date && v.end_date && v.sanction_reference
    && v.sanctioned_by && v.sanctioned_on;

  return (
    <Container size="xl">
      <PageHeader title="Offline Leave"
        subtitle="Record leave already sanctioned on paper. This synchronises records; it is not an approval." />
      <Card withBorder padding="lg" mb="lg">
        <Stack>
          <EmployeePicker label="Employee" value={v.user_id}
            onChange={(user_id) => setV({ ...v, user_id })} />
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            <Select label="Leave" allowDeselect={false} value={v.category}
              data={Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }))}
              onChange={(c) => setV({ ...v, category: (c ?? "CL") as Category })} />
            <TextInput type="date" label="From" value={v.start_date}
              onChange={(e) => setV({ ...v, start_date: e.currentTarget.value })} />
            <TextInput type="date" label="To" value={v.end_date}
              onChange={(e) => setV({ ...v, end_date: e.currentTarget.value })} />
            <TextInput label="Sanction reference" value={v.sanction_reference}
              onChange={(e) => setV({ ...v, sanction_reference: e.currentTarget.value })} />
            <TextInput label="Sanctioned by" value={v.sanctioned_by}
              onChange={(e) => setV({ ...v, sanctioned_by: e.currentTarget.value })} />
            <TextInput type="date" label="Sanctioned on" value={v.sanctioned_on}
              onChange={(e) => setV({ ...v, sanctioned_on: e.currentTarget.value })} />
          </SimpleGrid>
          <TextInput label="Evidence note" value={v.evidence_note}
            onChange={(e) => setV({ ...v, evidence_note: e.currentTarget.value })} />
          <Group justify="flex-end">
            <Button disabled={!ready} loading={record.isPending}
              onClick={() => v.user_id != null && record.mutate({ ...v, user_id: v.user_id }, {
                onSuccess: () => { setV(EMPTY);
                  notifications.show({ color: "green", title: "Recorded", message: "" }); },
                onError: (e) => notifications.show({ color: "red", title: "Not recorded",
                  message: errorMessage(e) }),
              })}>Record</Button>
          </Group>
        </Stack>
      </Card>
      <Card withBorder padding="md">
        <DataTable rows={data?.results ?? []} loading={isPending} rowKey={(r) => r.id}
          empty={{ title: "No offline records" }}
          columns={[
            { key: "ref", header: "Reference", render: (r) => r.sanction_reference },
            { key: "who", header: "Employee",
              render: (r) => <Text size="sm">{r.leave.applicant_name || r.leave.user_id}</Text> },
            { key: "leave", header: "Leave",
              render: (r) => `${r.leave.category} ${r.leave.start_date} → ${r.leave.end_date}` },
            { key: "by", header: "Sanctioned by", render: (r) => `${r.sanctioned_by}, ${r.sanctioned_on}` },
          ]} />
      </Card>
    </Container>
  );
}
