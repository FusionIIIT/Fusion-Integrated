import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaFileUpload, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAttorneyAssignments,
  useRespondAttorneyAssignment,
} from "../api/hooks";
import type { AttorneyAssignment } from "../api/types";
import { FilingRecordModal } from "../components/FilingRecordModal";
import { StatusBadge } from "../components/StatusBadge";

export default function AttorneyConsolePage() {
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [filingModalOpened, setFilingModalOpened] = useState(false);

  const { data, isPending, error } = useAttorneyAssignments();
  const [activeAssignId, setActiveAssignId] = useState<number | null>(null);

  const respondMutation = useRespondAttorneyAssignment(activeAssignId ?? 0);

  const handleRespond = async (id: number, accept: boolean) => {
    setActiveAssignId(id);
    try {
      await respondMutation.mutateAsync({
        accept,
        remarks: accept ? "Accepted without conflict of interest." : "Declined due to conflict of interest.",
      });
      notifications.show({
        color: accept ? "green" : "orange",
        message: accept ? "Assignment accepted (BR-PMS-022)." : "Assignment declined (BR-PMS-023).",
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<AttorneyAssignment>[] = [
    {
      key: "application_id",
      header: "Application ID",
      render: (row) => (
        <Text fw={600} size="sm">
          #{row.application_id}
        </Text>
      ),
    },
    {
      key: "status",
      header: "Assignment Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "remarks",
      header: "Instructions / Remarks",
      render: (row) => (
        <Text size="xs" c="dimmed">
          {row.remarks || "No instructions provided."}
        </Text>
      ),
    },
    {
      key: "created_at",
      header: "Offered At",
      render: (row) => (
        <Text size="xs">{new Date(row.created_at).toLocaleDateString()}</Text>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Group justify="flex-end" gap="xs">
          {row.status === "offered" ? (
            <>
              <Button
                size="xs"
                color="teal"
                leftSection={<FaCheck />}
                onClick={() => handleRespond(row.id, true)}
                loading={respondMutation.isPending && activeAssignId === row.id}
              >
                Accept
              </Button>
              <Button
                size="xs"
                color="red"
                variant="light"
                leftSection={<FaTimes />}
                onClick={() => handleRespond(row.id, false)}
                loading={respondMutation.isPending && activeAssignId === row.id}
              >
                Decline (Conflict)
              </Button>
            </>
          ) : row.status === "accepted" ? (
            <Button
              size="xs"
              color="blue"
              variant="light"
              leftSection={<FaFileUpload />}
              onClick={() => {
                setSelectedAppId(row.application_id);
                setFilingModalOpened(true);
              }}
            >
              Record Official Filing
            </Button>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Patent Attorney Console"
        subtitle="Docket management, assignment acceptance, conflict screening, and statutory filing execution."
      />

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No attorney assignments",
            description: "No patent applications currently pending in docket.",
          }}
        />
      </Card>

      <FilingRecordModal
        applicationId={selectedAppId}
        opened={filingModalOpened}
        onClose={() => setFilingModalOpened(false)}
      />
    </Container>
  );
}
