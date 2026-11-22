import { useState } from "react";
import {
  Button, Card, Container, Drawer, Group, Stack, Text,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { FaFileMedical, FaPills } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useMyPrescriptions, useMyRecords, useRecordDownload,
} from "../api/hooks";
import type { Prescription, Visit } from "../api/types";

export default function MyRecordsPage() {
  const { data, isPending, error } = useMyRecords();
  const { data: prescriptions } = useMyPrescriptions();
  const { can } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<number | null>(null);
  const canSubmitClaim = can("phc.reimbursement.submit");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="My Medical Records"
        subtitle="Your visits and the prescriptions recorded against them"
        action={canSubmitClaim && (
          <Button
            size="xs" variant="light" onClick={() => navigate("/phc/claims")}
          >
            My claims
          </Button>
        )}
      />

      <Card padding="lg">
        <DataTable<Visit>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={720}
          columns={[
            {
              key: "visit_date", header: "Visit",
              render: (r) => new Date(r.visit_date).toLocaleString(),
            },
            {
              key: "notes", header: "Notes",
              render: (r) => <Text size="sm">{r.notes || "—"}</Text>,
            },
            {
              key: "recorded_by", header: "Recorded by",
              render: (r) => r.recorded_by ?? "—",
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Button
                  size="xs" variant="subtle"
                  onClick={() => setSelected(r.id)}
                  disabled={!can("phc.records.view_self")}
                >
                  View
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaFileMedical,
            title: "No visits recorded",
            description: "Consultations recorded at the PHC will appear here.",
          }}
        />
      </Card>

      <RecordDrawer
        visitId={selected}
        onClose={() => setSelected(null)}
        records={data?.results ?? []}
        prescriptions={prescriptions?.results ?? []}
      />
    </Container>
  );
}

function RecordDrawer({ visitId, onClose, records, prescriptions }: {
  visitId: number | null;
  onClose: () => void;
  records: Visit[];
  prescriptions: Prescription[];
}) {
  const download = useRecordDownload();
  const visit = records.find((r) => r.id === visitId);
  const meds = prescriptions.filter((p) => p.visit === visitId);

  return (
    <Drawer
      opened={visitId != null} onClose={onClose} position="right" size="md"
      title={<Text fw={700}>Visit #{visitId ?? "—"}</Text>}
    >
      {!visit && <Text size="sm" c="gray.7">No record details available.</Text>}
      {visit && (
        <Stack gap="md">
          <Group gap="xl">
            <Stack gap={0}>
              <Text size="xs" c="gray.7" tt="uppercase">Date</Text>
              <Text size="sm">{new Date(visit.visit_date).toLocaleString()}</Text>
            </Stack>
            <Stack gap={0}>
              <Text size="xs" c="gray.7" tt="uppercase">Patient</Text>
              <Text size="sm">{visit.patient}</Text>
            </Stack>
          </Group>
          <div>
            <Text fw={600} size="sm" mb={4}>Consultation notes</Text>
            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
              {visit.notes || "No notes recorded."}
            </Text>
          </div>
          <div>
            <Text fw={600} size="sm" mb={6}>Prescriptions</Text>
            {meds.length === 0 ? (
              <Card padding="md">
                <Stack align="center" gap={4}>
                  <FaPills size={20} color="var(--mantine-color-gray-5)" />
                  <Text size="sm" c="gray.7">
                    No medicine was prescribed at this visit.
                  </Text>
                </Stack>
              </Card>
            ) : (
              <Stack gap={6}>
                {meds.map((p) => (
                  <Group key={p.id} justify="space-between">
                    <Text size="sm">{p.medicine}</Text>
                    <Text size="sm" c="gray.7">{p.dosage || "—"}</Text>
                  </Group>
                ))}
              </Stack>
            )}
          </div>
          <Group>
            <Button
              size="xs" variant="light" loading={download.isPending}
              onClick={() => download.mutate(visit.id)}
            >
              Download PDF
            </Button>
          </Group>
          {download.isError && (
            <Text size="sm" c="red.9">{errorMessage(download.error)}</Text>
          )}
        </Stack>
      )}
    </Drawer>
  );
}
