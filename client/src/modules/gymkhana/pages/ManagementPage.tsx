import { useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useConfirmClub, useCreateClub, useClubs } from "../api/hooks";

export default function ManagementPage() {
  const { can } = useAuth();
  const clubs = useClubs();
  const createClub = useCreateClub();
  const confirmClub = useConfirmClub();
  const [name, setName] = useState("");

  function create() {
    createClub.mutate({
      name,
      category: "Cultural",
      description: "",
      coordinator_id: 0,
      co_coordinator_id: 0,
      faculty_councillor_id: 0,
    }, {
      onSuccess: () => notifications.show({ color: "green", title: "Club created", message: name }),
      onError: (error) => notifications.show({ color: "red", title: "Could not create", message: errorMessage(error) }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Club management" subtitle="Create and confirm Gymkhana clubs" />
      {can("gymkhana.club.create") && (
        <Card padding="lg" mb="md">
          <Group>
            <TextInput label="Club name" value={name} onChange={(event) => setName(event.currentTarget.value)} />
            <Button mt={24} disabled={!name.trim()} loading={createClub.isPending} onClick={create}>Create club</Button>
          </Group>
        </Card>
      )}
      <Card padding="lg">
        <DataTable
          rows={clubs.data ?? []}
          loading={clubs.isPending}
          rowKey={(club) => club.id}
          columns={[
            { key: "name", header: "Club", render: (club) => <Stack gap={0}><Text fw={600}>{club.name}</Text><Text size="xs">{club.category}</Text></Stack> },
            { key: "status", header: "Status", render: (club) => <Badge color={club.status === "confirmed" ? "teal" : "yellow"}>{club.status}</Badge> },
            { key: "action", header: "", align: "right", render: (club) => can("gymkhana.club.approve") && club.status === "open" ? <Button size="xs" loading={confirmClub.isPending} onClick={() => confirmClub.mutate(club.id)}>Confirm</Button> : null },
          ]}
          empty={{ title: "No clubs", description: "No Gymkhana clubs have been registered." }}
        />
      </Card>
    </Container>
  );
}
