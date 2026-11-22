import { useState } from "react";
import {
  Badge, Button, Card, Center, Container, Group, Loader, Radio, Stack, Text, ThemeIcon,
} from "@mantine/core";
import { FaVoteYea } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useOpenPolls, useVote } from "../api/hooks";
import type { Poll } from "../api/types";
import { notifyDone, notifyFailed } from "../components/notify";

/** UC-GYM-007: polls addressed to the student's batch and branch, one vote each. */
export default function PollsPage() {
  const { data, isPending, error } = useOpenPolls();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  const polls = data?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader title="Polls" subtitle="Open polls addressed to your batch and branch" />
      {isPending ? <Center py="xl"><Loader size="sm" /></Center>
        : polls.length === 0 ? (
          <Card padding="lg"><Center py={48}><Stack align="center" gap={4}>
            <ThemeIcon size={48} radius="xl" variant="light" color="gray">
              <FaVoteYea size={20} /></ThemeIcon>
            <Text fw={600}>No open polls for you</Text>
            <Text size="sm" c="dimmed">A poll appears here while it is open and addressed to
              your batch and branch.</Text>
          </Stack></Center></Card>
        ) : <Stack>{polls.map((p) => <PollCard key={p.id} poll={p} />)}</Stack>}
    </Container>
  );
}

function PollCard({ poll }: { poll: Poll }) {
  const { can } = useAuth();
  const vote = useVote();
  const [choice, setChoice] = useState<string | null>(null);
  const voted = poll.choices.find((c) => c.id === poll.my_choice_id);

  function submit() {
    if (!choice) return;
    vote.mutate({ pollId: poll.id, choice_id: Number(choice) }, {
      onSuccess: () => notifyDone("Vote recorded", `Your vote in "${poll.title}" is counted.`),
      onError: (e) => notifyFailed("Vote not recorded", e),
    });
  }

  return (
    <Card padding="lg" withBorder>
      <Group justify="space-between" mb="xs">
        <Text fw={700}>{poll.title}</Text>
        <Badge variant="light">{poll.club_name} · open until {poll.expires_on}</Badge>
      </Group>
      <Text size="sm" c="dimmed" mb="md">{poll.description}</Text>
      {voted ? (
        <Text size="sm">You voted for <b>{voted.label}</b>.</Text>
      ) : (
        <Stack>
          <Radio.Group label="Your choice" value={choice} onChange={setChoice}>
            <Stack gap="xs" mt="xs">
              {poll.choices.map((c) => <Radio key={c.id} value={String(c.id)} label={c.label} />)}
            </Stack>
          </Radio.Group>
          {can("gymkhana.vote.create") && (
            <Group><Button onClick={submit} disabled={!choice} loading={vote.isPending}>
              Vote</Button></Group>)}
        </Stack>
      )}
    </Card>
  );
}
