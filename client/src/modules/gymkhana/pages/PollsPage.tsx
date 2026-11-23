import { useState } from "react";
import {
  Badge, Button, Card, Center, Container, Group, Loader, Progress, Radio, Stack, Text,
} from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useAccess, usePolls, useVote } from "../api/hooks";
import type { Poll } from "../api/types";
import { dateTime } from "../components/format";
import { LoadMore } from "../components/LoadMore";
import { PageError } from "../components/PageError";
import { done, refused } from "../components/toasts";

export default function PollsPage() {
  const access = useAccess();
  const polls = usePolls();
  const error = polls.error ?? access.error;
  if (error) return <PageError error={error} />;

  const open = polls.rows.filter(
    (p) => p.status === "active" && new Date(p.expires_at) > new Date());

  return (
    <Container size="md">
      <PageHeader title="Voting Polls" subtitle="Polls addressed to your batch and branch" />
      {polls.loading || access.loading ? (
        <Center py="xl"><Loader size="sm" aria-label="Loading polls" /></Center>
      ) : open.length === 0 ? (
        <Card padding="lg"><Text ta="center" c="dimmed">No open polls for you right now.</Text></Card>
      ) : (
        <Stack gap="md">
          {open.map((p) => (
            <PollCard key={p.id} poll={p} mayVote={access.can("gymkhana.poll.vote")} />
          ))}
        </Stack>
      )}
      <LoadMore list={polls} />
    </Container>
  );
}

function PollCard({ poll, mayVote }: { poll: Poll; mayVote: boolean }) {
  const vote = useVote();
  const [choice, setChoice] = useState("");
  return (
    <Card withBorder padding="lg" component="section" aria-label={poll.title}>
      <Group justify="space-between" mb="xs">
        <Text fw={600}>{poll.title}</Text>
        {poll.has_voted && <Badge color="green" variant="light">Voted</Badge>}
      </Group>
      <Text size="sm" c="dimmed">{poll.club_name} · closes {dateTime(poll.expires_at)}</Text>
      {poll.description && <Text size="sm" mt="xs">{poll.description}</Text>}
      {poll.has_voted ? (
        <PollTally poll={poll} />
      ) : mayVote ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            vote.mutate({ id: poll.id, choice_id: Number(choice) }, {
              onSuccess: () => done("Vote recorded", `Your vote in "${poll.title}" is counted.`),
              onError: (err) => refused("Could not record your vote", err),
            });
          }}
        >
          <Radio.Group label="Choose one" value={choice} onChange={setChoice} mt="md">
            <Stack gap="xs" mt="xs">
              {poll.choices.map((c) => (
                <Radio key={c.id} value={String(c.id)} label={c.choice_text} />
              ))}
            </Stack>
          </Radio.Group>
          <Button type="submit" mt="md" disabled={!choice} loading={vote.isPending}>Vote</Button>
        </form>
      ) : null}
    </Card>
  );
}

export function PollTally({ poll }: { poll: Poll }) {
  const total = poll.choices.reduce((sum, c) => sum + c.vote_count, 0);
  return (
    <Stack gap="xs" mt="md">
      {poll.choices.map((c) => (
        <div key={c.id}>
          <Group justify="space-between">
            <Text size="sm">{c.choice_text}</Text>
            <Text size="sm" c="dimmed">{c.vote_count} of {total}</Text>
          </Group>
          <Progress value={total ? (c.vote_count / total) * 100 : 0}
            aria-label={`${c.choice_text} share`} />
        </div>
      ))}
    </Stack>
  );
}
