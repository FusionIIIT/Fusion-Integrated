import { useState } from "react";
import {
  Button, Card, Container, Group, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaAmbulance } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLogAmbulance } from "../api/hooks";
import type { AmbulanceLog } from "../api/types";

export default function AmbulancePage() {
  const { can } = useAuth();
  const canLog = can("phc.ambulance.log");
  const log = useLogAmbulance();
  const [timestamp, setTimestamp] = useState(() =>
    new Date().toISOString().slice(0, 16));
  const [patientName, setPatientName] = useState("");
  const [destination, setDestination] = useState("");
  const [logs, setLogs] = useState<AmbulanceLog[]>([]);

  function submit() {
    log.mutate(
      {
        timestamp: new Date(timestamp).toISOString(),
        patient_name: patientName.trim(),
        destination: destination.trim(),
      },
      {
        onSuccess: (saved) => {
          setLogs((prev) => [saved, ...prev]);
          setPatientName("");
          setDestination("");
          notifications.show({
            color: "green", title: "Ambulance trip recorded",
            message: `${saved.patient_name} → ${saved.destination}.`,
          });
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not record trip", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Ambulance Logs"
        subtitle="Every ambulance usage recorded by the PHC office"
      />

      {canLog ? (
        <Card padding="lg" mb="md">
          {log.error && <ErrorState error={log.error} />}
          <Stack gap="md">
            <TextInput
              label="When" type="datetime-local" required value={timestamp}
              onChange={(e) => setTimestamp(e.currentTarget.value)}
            />
            <Group grow>
              <TextInput
                label="Patient name" required value={patientName}
                onChange={(e) => setPatientName(e.currentTarget.value)}
                maxLength={120}
              />
              <TextInput
                label="Destination" required value={destination}
                onChange={(e) => setDestination(e.currentTarget.value)}
                maxLength={200}
              />
            </Group>
            <Group justify="flex-end">
              <Button
                onClick={submit} loading={log.isPending}
                disabled={!timestamp || !patientName.trim() || !destination.trim()}
              >
                Record trip
              </Button>
            </Group>
          </Stack>
        </Card>
      ) : (
        <Text c="red" size="sm" mb="md">
          You do not have permission to record ambulance usage.
        </Text>
      )}

      <Card padding="lg">
        <DataTable<AmbulanceLog>
          rows={logs}
          rowKey={(r) => r.id}
          minWidth={760}
          columns={[
            { key: "timestamp", header: "When",
              render: (r) => new Date(r.timestamp).toLocaleString() },
            { key: "patient_name", header: "Patient",
              render: (r) => <Text fw={600}>{r.patient_name}</Text> },
            { key: "destination", header: "Destination" },
            { key: "logged_by", header: "Logged by",
              render: (r) => r.logged_by ?? "—" },
          ]}
          empty={{
            icon: FaAmbulance,
            title: "No trips recorded",
            description: "Ambulance trips recorded in this session will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
