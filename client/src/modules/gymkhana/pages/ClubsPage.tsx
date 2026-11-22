import { useEffect, useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUsers } from "react-icons/fa";

import { errorMessage, http } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

type Club = {
  id: number;
  name: string;
  category: string;
  description: string;
  status: "open" | "confirmed";
};

export default function ClubsPage() {
  const [clubs, setClubs] = useState<Club[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  async function loadClubs() {
    setLoading(true);
    try {
      const response = await http.get<Club[]>("/gymkhana/clubs/");
      setClubs(response.data);
      setError(null);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadClubs();
  }, []);

  async function apply(club: Club) {
    try {
      await http.post(`/gymkhana/clubs/${club.id}/memberships/apply/`, {});
      notifications.show({
        color: "green",
        title: "Application submitted",
        message: `Your application to ${club.name} is open.`,
      });
    } catch (caught) {
      notifications.show({
        color: "red",
        title: "Could not apply",
        message: errorMessage(caught),
      });
    }
  }

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Gymkhana clubs"
        subtitle="Confirmed clubs, categories and membership applications"
      />
      <Card padding="lg">
        <DataTable<Club>
          rows={clubs}
          loading={loading}
          rowKey={(club) => club.id}
          minWidth={760}
          columns={[
            {
              key: "name",
              header: "Club",
              render: (club) => (
                <Stack gap={0}>
                  <Text fw={600}>{club.name}</Text>
                  <Text size="xs" c="dimmed">{club.category}</Text>
                </Stack>
              ),
            },
            {
              key: "description",
              header: "Description",
              render: (club) => club.description || "—",
            },
            {
              key: "status",
              header: "Status",
              render: (club) => (
                <Badge
                  color={club.status === "confirmed" ? "teal" : "yellow"}
                  variant="light"
                >
                  {club.status}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "",
              align: "right",
              render: (club) => (
                <Group justify="flex-end" wrap="nowrap">
                  {club.status === "confirmed" && (
                    <Button
                      size="xs"
                      leftSection={<FaUsers size={10} />}
                      onClick={() => void apply(club)}
                    >
                      Apply
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaUsers,
            title: "No clubs available",
            description: "Confirmed Gymkhana clubs will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
