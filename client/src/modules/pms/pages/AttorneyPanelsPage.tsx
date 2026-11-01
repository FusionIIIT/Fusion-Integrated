import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaUserTie } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAttorneyPanels, useCreateAttorneyPanel } from "../api/hooks";
import type { AttorneyPanel } from "../api/types";

export default function AttorneyPanelsPage() {
  const [modalOpened, setModalOpened] = useState(false);
  const [name, setName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [email, setEmail] = useState("");
  const [specialization, setSpecialization] = useState("Electronics, Telecom & Software");
  const [userId, setUserId] = useState<number | string>(7001);
  const [maxWorkload, setMaxWorkload] = useState<number | string>(10);

  const { data, isPending, error } = useAttorneyPanels();
  const createMutation = useCreateAttorneyPanel();

  const handleCreate = async () => {
    if (!name.trim() || !firmName.trim() || !email.trim()) return;

    try {
      await createMutation.mutateAsync({
        user_id: Number(userId),
        name: name.trim(),
        firm_name: firmName.trim(),
        email: email.trim(),
        specialization: specialization.trim(),
        max_workload: Number(maxWorkload) || 10,
        is_active: true,
      });
      notifications.show({
        color: "green",
        message: "Attorney empaneled successfully (BR-PMS-021).",
      });
      setModalOpened(false);
      setName("");
      setFirmName("");
      setEmail("");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<AttorneyPanel>[] = [
    {
      key: "name",
      header: "Attorney & Law Firm",
      render: (row) => (
        <Group gap="sm">
          <FaUserTie color="#12b886" />
          <div>
            <Text fw={600} size="sm">
              {row.name}
            </Text>
            <Text size="xs" c="dimmed">
              {row.firm_name} | {row.email}
            </Text>
          </div>
        </Group>
      ),
    },
    {
      key: "specialization",
      header: "Technical Specialization",
      render: (row) => (
        <Text size="xs">{row.specialization}</Text>
      ),
    },
    {
      key: "workload",
      header: "Workload Capacity",
      render: (row) => (
        <Group gap="xs">
          <Badge
            color={row.current_workload >= row.max_workload ? "red" : "teal"}
            size="sm"
          >
            {row.current_workload} / {row.max_workload} Active
          </Badge>
        </Group>
      ),
    },
    {
      key: "is_active",
      header: "Empanelment Status",
      render: (row) => (
        <Badge color={row.is_active ? "green" : "gray"} size="sm">
          {row.is_active ? "ACTIVE" : "INACTIVE"}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Empaneled Since",
      render: (row) => (
        <Text size="xs">{new Date(row.created_at).toLocaleDateString()}</Text>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Institutional Patent Attorney Panel"
        subtitle="Empaneled IP legal counsel, technical specialization matrices, and active docket capacity limits (BR-PMS-021)."
        action={
          <Button
            leftSection={<FaPlus />}
            color="teal"
            onClick={() => setModalOpened(true)}
          >
            Empanel New Attorney
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
            title: "No attorneys empaneled",
            description: "Empanel qualified patent attorneys to handle institutional filings.",
          }}
        />
      </Card>

      <FormModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Empanel Patent Attorney"
        onSubmit={handleCreate}
        submitLabel="Empanel Attorney"
        submitting={createMutation.isPending}
        disabled={!name.trim() || !firmName.trim() || !email.trim()}
        disabledReason={!name.trim() ? "Attorney name and firm required" : undefined}
      >
        <Stack gap="md">
          <TextInput
            label="Attorney Full Name"
            placeholder="E.g. Adv. R. K. Singhania"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <TextInput
            label="Law Firm / Agency Name"
            placeholder="E.g. Apex IP Associates LLP"
            value={firmName}
            onChange={(e) => setFirmName(e.target.value)}
            required
          />

          <TextInput
            label="Professional Email"
            type="email"
            placeholder="attorney@apexip.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <TextInput
            label="Technical Specialization"
            value={specialization}
            onChange={(e) => setSpecialization(e.target.value)}
            required
          />

          <Group grow>
            <NumberInput
              label="System User ID"
              value={userId}
              onChange={setUserId}
              min={1}
              required
            />

            <NumberInput
              label="Max Concurrent Workload (BR-PMS-021)"
              value={maxWorkload}
              onChange={setMaxWorkload}
              min={1}
              max={50}
              required
            />
          </Group>
        </Stack>
      </FormModal>
    </Container>
  );
}
