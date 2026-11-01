import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClock, FaEdit, FaPaperPlane, FaPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useOfficeActions,
  useSubmitOfficeActionResponse,
} from "../api/hooks";
import type { OfficeAction } from "../api/types";
import { OfficeActionModal } from "../components/OfficeActionModal";
import { OfficeActionResponseModal } from "../components/OfficeActionResponseModal";
import { StatusBadge } from "../components/StatusBadge";

export default function OfficeActionsPage() {
  const [newOaModalOpened, setNewOaModalOpened] = useState(false);
  const [selectedActionId, setSelectedActionId] = useState<number | null>(null);
  const [responseModalOpened, setResponseModalOpened] = useState(false);

  const { data, isPending, error } = useOfficeActions();
  const submitResponseMutation = useSubmitOfficeActionResponse(0);

  const handleSubmitResponse = async (responseId: number) => {
    try {
      await submitResponseMutation.mutateAsync({
        submission_details: `Official response ${responseId} filed via IPO e-filing portal.`,
      });
      notifications.show({
        color: "green",
        message: "Office Action response officially submitted (BR-PMS-044).",
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<OfficeAction>[] = [
    {
      key: "action_number",
      header: "Action Reference",
      render: (row) => (
        <Stack gap={2}>
          <Text fw={600} size="sm">
            {row.action_number}
          </Text>
          <Text size="xs" c="dimmed">
            Type: {row.action_type} | App #{row.application_id}
          </Text>
        </Stack>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "response_deadline",
      header: "Statutory Deadline",
      render: (row) => (
        <Group gap="xs">
          <FaClock size={12} color="#fa5252" />
          <Text size="xs" fw={600} c="red">
            {row.response_deadline}
          </Text>
        </Group>
      ),
    },
    {
      key: "description",
      header: "Examiner Summary",
      render: (row) => (
        <Text size="xs" lineClamp={2}>
          {row.description}
        </Text>
      ),
    },
    {
      key: "responses",
      header: "Draft Responses",
      render: (row) => (
        <Badge size="xs" variant="light" color={row.responses?.length ? "teal" : "gray"}>
          {row.responses?.length ?? 0} Draft(s)
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Group justify="flex-end" gap="xs">
          <Button
            size="xs"
            variant="light"
            leftSection={<FaEdit />}
            onClick={() => {
              setSelectedActionId(row.id);
              setResponseModalOpened(true);
            }}
          >
            Draft Response
          </Button>
          {row.responses?.[0]?.id != null && !row.responses[0].submitted_at && (
            <Button
              size="xs"
              color="teal"
              leftSection={<FaPaperPlane />}
              onClick={() => {
                const respId = row.responses?.[0]?.id;
                if (respId) handleSubmitResponse(respId);
              }}
            >
              Submit Response
            </Button>
          )}
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Office Actions & Examination Reports"
        subtitle="First Examination Reports (FER), Second Examination Reports (SER), hearing notices, and rebuttal responses."
        action={
          <Button
            leftSection={<FaPlus />}
            color="orange"
            onClick={() => setNewOaModalOpened(true)}
          >
            Log Office Action
          </Button>
        }
      />

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No office actions",
            description: "No active office actions or examination reports logged.",
          }}
        />
      </Card>

      <OfficeActionModal
        applicationId={1}
        opened={newOaModalOpened}
        onClose={() => setNewOaModalOpened(false)}
      />

      <OfficeActionResponseModal
        actionId={selectedActionId}
        opened={responseModalOpened}
        onClose={() => setResponseModalOpened(false)}
      />
    </Container>
  );
}
