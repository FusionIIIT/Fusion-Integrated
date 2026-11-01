import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert, Button, Card, Container, Group, Stack, Text, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { http } from "../../../lib/http";
import type { Club, Results } from "../api/types";

export default function ClubsPage() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Club | null>(null);
  const [achievements, setAchievements] = useState("");
  const [statement, setStatement] = useState("");

  const clubs = useQuery({
    queryKey: ["gymkhana", "clubs"],
    queryFn: async () =>
      (await http.get<Results<Club>>("/gymkhana/clubs")).data.results,
  });

  const apply = useMutation({
    mutationFn: async () =>
      (await http.post("/gymkhana/applications/mine", {
        club_id: selected!.id, achievements, statement,
      })).data,
    onSuccess: () => {
      notifications.show({ title: "Application submitted", message: "You can track its status under My Applications." });
      setSelected(null);
      setAchievements("");
      setStatement("");
      qc.invalidateQueries({ queryKey: ["gymkhana", "my-applications"] });
    },
    onError: () =>
      notifications.show({
        color: "red",
        title: "Could not submit application",
        message: "Check whether you already applied, then try again.",
      }),
  });

  return (
    <Container size="lg" py="lg">
      <Stack>
        <Title order={2}>Gymkhana Clubs</Title>
        <Text c="dimmed">Explore active clubs and apply for membership.</Text>
        {clubs.isLoading && <Text>Loading clubs…</Text>}
        {clubs.isError && <Alert color="red" title="Unable to load clubs">Please refresh and try again.</Alert>}
        <Stack>
          {clubs.data?.map((club) => (
            <Card withBorder key={club.id} radius="md">
              <Group justify="space-between" align="flex-start">
                <Stack gap={4} style={{ flex: 1 }}>
                  <Title order={4}>{club.name}</Title>
                  <Text size="sm" c="dimmed">{club.code}</Text>
                  <Text>{club.description || "No description provided."}</Text>
                </Stack>
                <Button onClick={() => setSelected(club)}>Apply</Button>
              </Group>
            </Card>
          ))}
          {clubs.data?.length === 0 && <Text>No active clubs are available right now.</Text>}
        </Stack>
        {selected && (
          <Card withBorder>
            <Stack>
              <Title order={3}>Apply to {selected.name}</Title>
              <Textarea
                label="Achievements"
                description="Optional"
                value={achievements}
                onChange={(e) => setAchievements(e.currentTarget.value)}
                maxLength={5000}
              />
              <Textarea
                label="Why do you want to join?"
                description="Optional"
                value={statement}
                onChange={(e) => setStatement(e.currentTarget.value)}
                maxLength={5000}
              />
              <Group>
                <Button loading={apply.isPending} onClick={() => apply.mutate()}>
                  Submit application
                </Button>
                <Button variant="default" onClick={() => setSelected(null)}>Cancel</Button>
              </Group>
            </Stack>
          </Card>
        )}
      </Stack>
    </Container>
  );
}
