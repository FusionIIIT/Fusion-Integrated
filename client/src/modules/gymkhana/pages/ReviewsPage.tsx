import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert, Badge, Button, Card, Container, Group, Select, Stack, Text,
  Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { http } from "../../../lib/http";
import type { Application, Club, Results } from "../api/types";

export default function ReviewsPage() {
  const qc = useQueryClient();
  const [clubId, setClubId] = useState<string | null>(null);
  const [remarks, setRemarks] = useState<Record<number, string>>({});

  const clubs = useQuery({
    queryKey: ["gymkhana", "assigned-clubs"],
    queryFn: async () =>
      (await http.get<Results<Club>>("/gymkhana/clubs/assigned")).data.results,
  });

  const applications = useQuery({
    queryKey: ["gymkhana", "club-applications", clubId],
    queryFn: async () =>
      (await http.get<Results<Application>>(
        `/gymkhana/clubs/${clubId}/applications`,
      )).data.results,
    enabled: clubId !== null,
  });

  const review = useMutation({
    mutationFn: async (input: {
      id: number; decision: "approved" | "rejected";
    }) =>
      (await http.post(`/gymkhana/applications/${input.id}/review`, {
        decision: input.decision,
        remarks: remarks[input.id] ?? "",
      })).data,
    onSuccess: () => {
      notifications.show({ title: "Review saved", message: "The application status has been updated." });
      qc.invalidateQueries({ queryKey: ["gymkhana", "club-applications", clubId] });
    },
    onError: () =>
      notifications.show({
        color: "red",
        title: "Review failed",
        message: "You may not be assigned to this club, or the application was already reviewed.",
      }),
  });

  return (
    <Container size="lg" py="lg">
      <Stack>
        <Title order={2}>Membership Reviews</Title>
        <Text c="dimmed">Review applications for clubs assigned to you.</Text>
        {clubs.isLoading && <Text>Loading your assigned clubs…</Text>}
        {clubs.isError && <Alert color="red" title="Unable to load clubs">Check your review permissions and refresh.</Alert>}
        {clubs.data && (
          <Select
            label="Select club"
            placeholder="Choose a club"
            data={clubs.data.map((club) => ({
              value: String(club.id), label: club.name,
            }))}
            value={clubId}
            onChange={setClubId}
            clearable
          />
        )}
        {clubs.data?.length === 0 && <Text>You have no active club assignments.</Text>}
        {applications.isLoading && <Text>Loading applications…</Text>}
        {applications.isError && <Alert color="red" title="Unable to load applications">Please select the club again or refresh.</Alert>}
        {applications.data?.map((app) => (
          <Card withBorder key={app.id}>
            <Stack>
              <Group justify="space-between">
                <Title order={4}>Application #{app.id}</Title>
                <Badge color={app.status === "approved" ? "green" : app.status === "rejected" ? "red" : "yellow"}>
                  {app.status.toUpperCase()}
                </Badge>
              </Group>
              <Text>Student ID: {app.student_id}</Text>
              {app.achievements && <Text>Achievements: {app.achievements}</Text>}
              {app.statement && <Text>Statement: {app.statement}</Text>}
              {app.status === "open" && (
                <>
                  <Textarea
                    label="Review remarks"
                    value={remarks[app.id] ?? ""}
                    onChange={(e) =>
                      setRemarks((old) => ({ ...old, [app.id]: e.currentTarget.value }))
                    }
                    maxLength={2000}
                  />
                  <Group>
                    <Button
                      loading={review.isPending}
                      onClick={() => review.mutate({ id: app.id, decision: "approved" })}
                    >
                      Approve
                    </Button>
                    <Button
                      color="red"
                      variant="light"
                      loading={review.isPending}
                      onClick={() => review.mutate({ id: app.id, decision: "rejected" })}
                    >
                      Reject
                    </Button>
                  </Group>
                </>
              )}
              {app.review_remarks && <Text size="sm">Previous remarks: {app.review_remarks}</Text>}
            </Stack>
          </Card>
        ))}
        {clubId && applications.data?.length === 0 && (
          <Text>No applications have been submitted to this club.</Text>
        )}
      </Stack>
    </Container>
  );
}
