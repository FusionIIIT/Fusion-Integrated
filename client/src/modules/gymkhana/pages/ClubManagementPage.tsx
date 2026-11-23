import { useState } from "react";
import { Alert, Card, Center, Container, Loader, Select, Tabs, Text } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useAccess } from "../api/hooks";
import { ApplicationsPanel } from "../components/manage/ApplicationsPanel";
import { BookingsPanel } from "../components/manage/BookingsPanel";
import { BudgetsPanel } from "../components/manage/BudgetsPanel";
import { LeadershipPanel } from "../components/manage/LeadershipPanel";
import { PollsPanel } from "../components/manage/PollsPanel";
import { ReportPanel } from "../components/manage/ReportPanel";
import { PageError } from "../components/PageError";

export default function ClubManagementPage() {
  const access = useAccess();
  const [picked, setPicked] = useState<string | null>(null);
  if (access.error) return <PageError error={access.error} />;

  const club = access.clubsLed.find((c) => String(c.id) === picked) ?? access.clubsLed[0];
  return (
    <Container size="xl">
      <PageHeader title="Club Management" subtitle="For a club's coordinator and co-coordinator" />
      {access.loading ? (
        <Center py="xl"><Loader size="sm" aria-label="Loading your clubs" /></Center>
      ) : !club ? (
        <Card padding="lg">
          <Text ta="center" c="dimmed">You do not lead a club.</Text>
        </Card>
      ) : (
        <>
          <Select
            label="Club" mb="md" maw={360} allowDeselect={false}
            data={access.clubsLed.map((c) => ({ value: String(c.id), label: c.name }))}
            value={String(club.id)} onChange={setPicked}
          />
          {club.status === "open" && (
            <Alert color="yellow" mb="md" title="Awaiting approval">
              Student Admin has not confirmed this club yet, so most actions are not available.
            </Alert>
          )}
          <Card padding="lg">
            <Tabs defaultValue="applications" keepMounted={false} key={club.id}>
              <Tabs.List mb="md">
                <Tabs.Tab value="applications">Applications</Tabs.Tab>
                <Tabs.Tab value="bookings">Bookings</Tabs.Tab>
                <Tabs.Tab value="polls">Polls</Tabs.Tab>
                <Tabs.Tab value="budgets">Budget requests</Tabs.Tab>
                <Tabs.Tab value="report">Event report</Tabs.Tab>
                <Tabs.Tab value="leadership">Leadership</Tabs.Tab>
              </Tabs.List>
              <Tabs.Panel value="applications"><ApplicationsPanel club={club} /></Tabs.Panel>
              <Tabs.Panel value="bookings"><BookingsPanel club={club} /></Tabs.Panel>
              <Tabs.Panel value="polls"><PollsPanel club={club} /></Tabs.Panel>
              <Tabs.Panel value="budgets"><BudgetsPanel club={club} /></Tabs.Panel>
              <Tabs.Panel value="report"><ReportPanel club={club} /></Tabs.Panel>
              <Tabs.Panel value="leadership"><LeadershipPanel club={club} /></Tabs.Panel>
            </Tabs>
          </Card>
        </>
      )}
    </Container>
  );
}
