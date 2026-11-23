import { useEffect, useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaVoteYea } from "react-icons/fa";

import { errorMessage, http } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

type Choice = { id: number; text: string; votes_count: number };
type Poll = {
  id: number;
  title: string;
  description: string;
  expires_at: string;
  choices: Choice[];
};

export default function PollsPage() {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [choiceIds, setChoiceIds] = useState<Record<number, string>>({});

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await http.get<Poll[]>("/gymkhana/polls/");
        if (active) setPolls(response.data);
      } catch (caught) {
        if (active) setError(caught);
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  async function vote(poll: Poll) {
    const choiceId = choiceIds[poll.id];
    if (!choiceId) return;
    try {
      await http.post(`/gymkhana/polls/${poll.id}/vote/`, {
        choice_id: Number(choiceId),
      });
      notifications.show({
        color: "green",
        title: "Vote recorded",
        message: `Your response to ${poll.title} was recorded.`,
      });
    } catch (caught) {
      notifications.show({
        color: "red",
        title: "Could not vote",
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
        title="Gymkhana polls"
        subtitle="Active polls for your batch and branch"
      />
      <Card padding="lg">
        <DataTable<Poll>
          rows={polls}
          loading={loading}
          rowKey={(poll) => poll.id}
          minWidth={760}
          columns={[
            {
              key: "title",
              header: "Poll",
              render: (poll) => (
                <Stack gap={0}>
                  <Text fw={600}>{poll.title}</Text>
                  <Text size="xs" c="dimmed">{poll.description || "—"}</Text>
                </Stack>
              ),
            },
            {
              key: "expires",
              header: "Expires",
              render: (poll) => (
                <Badge variant="light" color="blue">
                  {new Date(poll.expires_at).toLocaleString()}
                </Badge>
              ),
            },
            {
              key: "choice",
              header: "Choice",
              render: (poll) => (
                <Select
                  aria-label={`Choice for ${poll.title}`}
                  placeholder="Select choice"
                  data={poll.choices.map((choice) => ({
                    value: String(choice.id),
                    label: choice.text,
                  }))}
                  value={choiceIds[poll.id] ?? null}
                  onChange={(value) =>
                    setChoiceIds((current) => ({ ...current, [poll.id]: value ?? "" }))
                  }
                />
              ),
            },
            {
              key: "actions",
              header: "",
              align: "right",
              render: (poll) => (
                <Group justify="flex-end" wrap="nowrap">
                  <Button
                    size="xs"
                    leftSection={<FaVoteYea size={10} />}
                    disabled={!choiceIds[poll.id]}
                    onClick={() => void vote(poll)}
                  >
                    Vote
                  </Button>
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaVoteYea,
            title: "No active polls",
            description: "Polls targeted to you will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
