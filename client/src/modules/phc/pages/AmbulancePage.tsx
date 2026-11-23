import { useState } from "react";
import { Button, Container, Stack, Table, TextInput } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAmbulanceLogs, useLogAmbulance } from "../api/hooks";
import { ListStates } from "../components/ListStates";
import { LoadMore } from "../components/LoadMore";

export default function AmbulancePage() {
  const { can } = useAuth();
  const list = useAmbulanceLogs();
  const { data, isPending, error } = list;
  const log = useLogAmbulance();
  const [open, setOpen] = useState(false);
  const [usedAt, setUsedAt] = useState("");
  const [patient, setPatient] = useState("");
  const [destination, setDestination] = useState("");
  const rows = data?.results ?? [];

  const close = () => {
    setOpen(false);
    setUsedAt("");
    setPatient("");
    setDestination("");
    log.reset();
  };

  return (
    <Container size="lg">
      <PageHeader
        title="Ambulance log"
        subtitle="Every use of the PHC ambulance"
        action={can("phc.ambulance.create") && (
          <Button onClick={() => setOpen(true)}>Log ambulance use</Button>
        )}
      />
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No ambulance use logged" />
      {rows.length > 0 && (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>When</Table.Th><Table.Th>Patient</Table.Th>
              <Table.Th>Destination</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{new Date(r.used_at).toLocaleString()}</Table.Td>
                <Table.Td>{r.patient_name}</Table.Td>
                <Table.Td>{r.destination}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <LoadMore list={list} />
      <FormModal
        opened={open} onClose={close} title="Log ambulance use" submitting={log.isPending}
        error={log.error} disabled={!usedAt || !patient.trim() || !destination.trim()}
        disabledReason="Enter the time, the patient's name and the destination."
        onSubmit={() => log.mutate({
          used_at: new Date(usedAt).toISOString(), patient_name: patient, destination,
        }, { onSuccess: close })}
      >
        <Stack>
          <TextInput label="Date and time" type="datetime-local" required value={usedAt}
            onChange={(e) => setUsedAt(e.currentTarget.value)} />
          <TextInput label="Patient name" required value={patient}
            onChange={(e) => setPatient(e.currentTarget.value)} />
          <TextInput label="Destination" required value={destination}
            onChange={(e) => setDestination(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </Container>
  );
}
