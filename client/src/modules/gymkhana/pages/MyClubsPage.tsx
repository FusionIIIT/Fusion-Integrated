import { useState } from "react";
import {
  Button, Card, Center, Container, Group, Loader, SimpleGrid, Stack, Text, ThemeIcon,
} from "@mantine/core";
import { FaFlag } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyClubs } from "../api/hooks";
import type { Club } from "../api/types";
import {
  BudgetList, MembershipRequests, PollResults, ReportList,
} from "../components/ClubHeadDrawers";
import {
  BudgetForm, LeadershipForm, PollForm, ReportForm,
} from "../components/ClubHeadForms";

type Panel = "members" | "leadership" | "poll" | "results" | "budget" | "budgets"
  | "report" | "reports";

/** Club Head operations (BR-GYM-010), for the clubs one currently leads. */
export default function MyClubsPage() {
  const { data, isPending, error } = useMyClubs();
  const [open, setOpen] = useState<{ club: Club; panel: Panel } | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  const clubs = data?.leading ?? [];
  const close = () => setOpen(null);

  return (
    <Container size="xl">
      <PageHeader title="My Clubs" subtitle="Clubs you lead as coordinator or co-coordinator" />
      {isPending ? <Center py="xl"><Loader size="sm" /></Center>
        : clubs.length === 0 ? (
          <Card padding="lg"><Center py={48}><Stack align="center" gap={4}>
            <ThemeIcon size={48} radius="xl" variant="light" color="gray">
              <FaFlag size={20} /></ThemeIcon>
            <Text fw={600}>You do not lead a club</Text>
            <Text size="sm" c="dimmed" ta="center" maw={520}>Club Heads are the coordinator and
              co-coordinator of a confirmed club, as assigned by Student Admin or by the
              club's previous leaders.</Text>
          </Stack></Center></Card>
        ) : (
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            {clubs.map((c) => <ClubCard key={c.id} club={c}
              onOpen={(panel) => setOpen({ club: c, panel })} />)}
          </SimpleGrid>
        )}
      {open?.panel === "members" && <MembershipRequests club={open.club} onClose={close} />}
      {open?.panel === "leadership" && <LeadershipForm club={open.club} onClose={close} />}
      {open?.panel === "poll" && <PollForm club={open.club} onClose={close} />}
      {open?.panel === "results" && <PollResults club={open.club} onClose={close} />}
      {open?.panel === "budget" && <BudgetForm club={open.club} onClose={close} />}
      {open?.panel === "budgets" && <BudgetList club={open.club} onClose={close} />}
      {open?.panel === "report" && <ReportForm club={open.club} onClose={close} />}
      {open?.panel === "reports" && <ReportList club={open.club} onClose={close} />}
    </Container>
  );
}

function ClubCard({ club, onOpen }: { club: Club; onOpen: (p: Panel) => void }) {
  const { can } = useAuth();
  const actions: [Panel, string, string][] = [
    ["members", "Membership requests", "gymkhana.membership.approve"],
    ["leadership", "Change leadership", "gymkhana.leadership.assign"],
    ["poll", "New poll", "gymkhana.poll.create"],
    ["results", "Poll results", "gymkhana.poll.create"],
    ["budget", "Request budget", "gymkhana.budget_request.create"],
    ["budgets", "Budget requests", "gymkhana.budget_request.view"],
    ["report", "Submit event report", "gymkhana.event_report.create"],
    ["reports", "Event reports", "gymkhana.event_report.view"],
  ];
  return (
    <Card padding="lg" withBorder>
      <Text fw={700}>{club.name}</Text>
      <Text size="sm" c="dimmed" mb="md" lineClamp={2}>{club.description}</Text>
      <Group gap="xs">
        {actions.filter(([, , perm]) => can(perm)).map(([panel, label]) => (
          <Button key={panel} size="xs" variant="light" onClick={() => onOpen(panel)}
            aria-label={`${label} for ${club.name}`}>{label}</Button>))}
      </Group>
    </Card>
  );
}
