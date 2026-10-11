import { useState } from "react";
import {
  Alert, Button, Container, Group, Modal, Paper, Stack, Table, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAction, useApplications, useCancellation, useExtension } from "../api/hooks";
import type { LeaveApplication } from "../api/types";
import { StateBadge } from "../components/StateBadge";

function canCancel(row: LeaveApplication) {
  return row.request_kind === "new" && row.status === "approved"
    && row.start_date > new Date().toISOString().slice(0, 10);
}

function canExtend(row: LeaveApplication) {
  const today = new Date().toISOString().slice(0, 10);
  return row.request_kind === "new" && row.status === "approved"
    && ["EL", "COL", "VL"].includes(row.leave_type)
    && row.start_date <= today && row.end_date >= today;
}

export default function MyLeavePage() {
  const query = useApplications();
  const cancel = useCancellation();
  const extend = useExtension();
  const action = useAction();
  const [extensionFor, setExtensionFor] = useState<LeaveApplication | null>(null);
  const [extensionEnd, setExtensionEnd] = useState("");
  const [replacementId, setReplacementId] = useState<number | string>("");

  function run(actionFn: () => void) {
    actionFn();
  }

  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;
  const rows = query.data ?? [];
  return (
    <Container size="xl">
      <PageHeader title="My Leave Applications" subtitle="Applications, decisions, and lifecycle actions." />
      {rows.length === 0 ? <Alert color="gray">You have no leave applications yet.</Alert> : (
        <Paper withBorder p="md">
          <Table.ScrollContainer minWidth={850}>
            <Table striped highlightOnHover>
              <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Period</Table.Th>
                <Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
              <Table.Tbody>{rows.map((row) => <Table.Tr key={row.id}>
                <Table.Td>{row.leave_type}</Table.Td>
                <Table.Td>{row.start_date} – {row.end_date}</Table.Td>
                <Table.Td>{row.requested_days}</Table.Td>
                <Table.Td><StateBadge status={row.status} /></Table.Td>
                <Table.Td><Stack gap="xs">
                  <Button component="a" size="xs" variant="subtle"
                    href={`/api/v1/leave/applications/${row.id}/export`} target="_blank">
                    Printable copy
                  </Button>
                  {canCancel(row) && <Button size="xs" color="orange"
                    loading={cancel.isPending} onClick={() => run(() => cancel.mutate(row.id, {
                      onSuccess: () => notifications.show({ title: "Cancellation requested", message: "Your request is awaiting review." }),
                      onError: (error) => notifications.show({ color: "red", title: "Could not request cancellation", message: errorMessage(error) }),
                    }))}>Request cancellation</Button>}
                  {canExtend(row) && <Button size="xs" variant="light"
                    onClick={() => setExtensionFor(row)}>Request extension</Button>}
                  {row.status === "applicant_action_required" && <Group wrap="nowrap">
                    <TextInput size="xs" placeholder="Replacement employee ID" value={replacementId}
                      onChange={(event) => setReplacementId(event.currentTarget.value)} />
                    <Button size="xs" loading={action.isPending} disabled={!replacementId}
                      onClick={() => action.mutate({ id: row.id, event: "replace_substitute",
                        substitute_user_id: Number(replacementId) }, {
                        onSuccess: () => setReplacementId(""),
                        onError: (error) => notifications.show({ color: "red", title: "Could not nominate substitute", message: errorMessage(error) }),
                      })}>Nominate</Button>
                  </Group>}</Stack></Table.Td>
              </Table.Tr>)}</Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Paper>
      )}
      {!query.isPending && rows.length > 0 && <Text size="xs" c="dimmed" mt="sm">
        Dates and decisions are shown in the application timezone.
      </Text>}
      <Modal opened={Boolean(extensionFor)} onClose={() => setExtensionFor(null)}
        title="Request leave extension">
        <Stack>
          <Text>Additional leave starts the day after the approved interval.</Text>
          <TextInput label="Extended end date" type="date" value={extensionEnd}
            onChange={(event) => setExtensionEnd(event.currentTarget.value)} />
          <Button loading={extend.isPending} disabled={!extensionFor || !extensionEnd}
            onClick={() => extensionFor && extend.mutate({
              original_application_id: extensionFor.id, end_date: extensionEnd,
            }, {
              onSuccess: () => { setExtensionFor(null); setExtensionEnd(""); },
              onError: (error) => notifications.show({ color: "red", title: "Could not request extension", message: errorMessage(error) }),
            })}>Submit extension</Button>
        </Stack>
      </Modal>
    </Container>
  );
}
