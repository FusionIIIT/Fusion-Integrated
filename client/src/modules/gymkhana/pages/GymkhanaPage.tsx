import { useMemo, useState, type FormEvent } from "react";
import {
  Alert, Badge, Button, Card, FileInput, Group, NumberInput, Select, Stack,
  Tabs, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useApply, useApproveClub, useApproveMembership, useAssignedReports,
  useBudgets, useChangeLeadership, useClubApplications, useClubEvents,
  useClubReports, useClubSessions, useClubs, useCreateBudget, useCreateClub,
  useCreateEvent, useCreatePoll, useCreateReport, useCreateSession, useMine,
  usePeople, usePolls, useVenues, useVote,
} from "../api/hooks";
import type { Club, DirectoryPerson } from "../api/types";

function formData(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  for (const [key, value] of [...data.entries()]) {
    if (value instanceof File && value.size === 0) data.delete(key);
  }
  return data;
}

function reportError(error: unknown, title: string) {
  notifications.show({ color: "red", title, message: errorMessage(error) });
}

function PersonPicker({ kind, label, name }: {
  kind: "student" | "faculty"; label: string; name: string;
}) {
  const [query, setQuery] = useState("");
  const [value, setValue] = useState<string | null>(null);
  const people = usePeople(kind, query);
  const options = (people.data ?? []).map((person: DirectoryPerson) => ({
    value: String(person.user_id),
    label: `${person.display_name} (${person.username})`,
  }));
  return (
    <>
      <Select
        label={label}
        placeholder="Search by name or username"
        searchable
        searchValue={query}
        onSearchChange={setQuery}
        value={value}
        onChange={setValue}
        data={options}
        nothingFoundMessage={query.length < 2 ? "Enter at least 2 characters" : "No match"}
        required
      />
      <input type="hidden" name={name} value={value ?? ""} />
    </>
  );
}

export default function GymkhanaPage() {
  const { session, can } = useAuth();
  const clubsQuery = useClubs();
  const venuesQuery = useVenues();
  const isFacultyReviewer = can("gymkhana.report.view");
  const isStudent = session?.user.kind === "student";
  const membershipsQuery = useMine(isStudent);
  const pollsQuery = usePolls(isStudent);
  const assignedReportsQuery = useAssignedReports(isFacultyReviewer);
  const createClub = useCreateClub();
  const approveClub = useApproveClub();
  const apply = useApply();
  const approveMembership = useApproveMembership();
  const createPoll = useCreatePoll();
  const vote = useVote();
  const changeLeadership = useChangeLeadership();
  const createSession = useCreateSession();
  const createEvent = useCreateEvent();
  const createBudget = useCreateBudget();
  const createReport = useCreateReport();

  const userId = session?.user.id ?? 0;
  const isAdmin = can("gymkhana.club.manage");
  const confirmedClubs = (clubsQuery.data ?? []).filter(
    (club) => club.status === "confirmed",
  );
  const myClubs = confirmedClubs.filter(
    (club) => club.coordinator_user_id === userId
      || club.co_coordinator_user_id === userId,
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedClub = useMemo(
    () => myClubs.find((club) => String(club.id) === selectedId) ?? myClubs[0] ?? null,
    [myClubs, selectedId],
  );
  const clubApplications = useClubApplications(selectedClub?.id ?? null);
  const sessions = useClubSessions(selectedClub?.id ?? null);
  const events = useClubEvents(selectedClub?.id ?? null);
  const budgets = useBudgets(selectedClub?.id ?? null);
  const reports = useClubReports(selectedClub?.id ?? null);

  if (clubsQuery.error) {
    return <ErrorState error={clubsQuery.error} />;
  }

  function submitClub(event: FormEvent<HTMLFormElement>) {
    const data = formData(event);
    createClub.mutate(data, {
      onSuccess: () => notifications.show({
        color: "green", title: "Club created", message: "The club is open for Student Admin confirmation.",
      }),
      onError: (error) => reportError(error, "Could not create club"),
    });
  }

  function submitPoll(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClub) return;
    const data = new FormData(event.currentTarget);
    const choices = String(data.get("choices") ?? "")
      .split("\n").map((choice) => choice.trim()).filter(Boolean);
    const targetGroups = String(data.get("target_groups") ?? "")
      .split("\n")
      .map((group) => group.split(",", 2).map((part) => part.trim()))
      .map(([batchYear, discipline]) => ({
        batch_year: Number(batchYear),
        discipline: discipline ?? "",
      }));
    const expires = String(data.get("expires_at") ?? "");
    createPoll.mutate({
      club_id: selectedClub.id,
      title: data.get("title"),
      description: data.get("description"),
      expires_at: new Date(expires).toISOString(),
      choices,
      target_groups: targetGroups,
    }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Poll created", message: "Targeted students were notified.",
      }),
      onError: (error) => reportError(error, "Could not create poll"),
    });
  }

  function submitLeadership(event: FormEvent<HTMLFormElement>) {
    const data = formData(event);
    if (!selectedClub) return;
    changeLeadership.mutate({
      id: selectedClub.id,
      data: {
        coordinator_user_id: Number(data.get("coordinator_user_id")),
        co_coordinator_user_id: Number(data.get("co_coordinator_user_id")),
      },
    }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Leadership updated", message: "The current Club Heads have been changed.",
      }),
      onError: (error) => reportError(error, "Could not change leadership"),
    });
  }

  function submitUpload(
    event: FormEvent<HTMLFormElement>,
    submit: (data: FormData) => void,
  ) {
    const data = formData(event);
    submit(data);
  }

  function uploadCallbacks(title: string) {
    return {
      onSuccess: () => notifications.show({
        color: "green", title, message: "Your submission was saved.",
      }),
      onError: (error: unknown) =>
        reportError(error, `Could not ${title.toLowerCase()}`),
    };
  }

  function applyToClub(event: FormEvent<HTMLFormElement>, club: Club) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    apply.mutate({
      id: club.id,
      data: { description: String(data.get("description") ?? "") },
    }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Application submitted", message: `Your application to ${club.name} is open.`,
      }),
      onError: (error) => reportError(error, "Could not apply"),
    });
  }

  function approveApplication(clubId: number, applicationId: number) {
    approveMembership.mutate({ clubId, applicationId, remarks: "" }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Membership approved", message: "The application is now confirmed.",
      }),
      onError: (error) => reportError(error, "Could not approve membership"),
    });
  }

  return (
    <Stack>
      <PageHeader title="Gymkhana" />
      {venuesQuery.data?.length === 0 && (
        <Alert color="yellow">
          Booking is disabled until GYMKHANA_VENUES is configured on the server.
        </Alert>
      )}
      <Tabs defaultValue="clubs">
        <Tabs.List>
          <Tabs.Tab value="clubs">Clubs</Tabs.Tab>
          {isStudent && <Tabs.Tab value="memberships">My memberships</Tabs.Tab>}
          {isStudent && <Tabs.Tab value="polls">Voting polls</Tabs.Tab>}
          {myClubs.length > 0 && <Tabs.Tab value="manage">Club operations</Tabs.Tab>}
          {isFacultyReviewer && <Tabs.Tab value="reports">Assigned reports</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="clubs" pt="md">
          {isAdmin && (
            <Card withBorder mb="md">
              <Text fw={600} mb="sm">Establish a club</Text>
              <form onSubmit={submitClub}>
                <Stack>
                  <TextInput name="name" label="Club name" required maxLength={150} />
                  <Select
                    name="category"
                    label="Category"
                    data={["Technical", "Sports", "Cultural"]}
                    required
                  />
                  <Group grow>
                    <PersonPicker kind="student" name="coordinator_user_id"
                      label="Coordinator" />
                    <PersonPicker kind="student" name="co_coordinator_user_id"
                      label="Co-coordinator" />
                  </Group>
                  <PersonPicker kind="faculty" name="faculty_councillor_user_id"
                    label="Faculty Councillor" />
                  <Textarea name="description" label="Description" required />
                  <Button type="submit" loading={createClub.isPending}>Create open club</Button>
                </Stack>
              </form>
            </Card>
          )}
          <Stack>
            {(clubsQuery.data ?? []).map((club) => {
              const prior = membershipsQuery.data?.find((item) => item.club === club.id);
              return (
                <Card key={club.id} withBorder>
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text fw={600}>{club.name}</Text>
                      <Text size="sm" c="dimmed">{club.category} · {club.description}</Text>
                    </div>
                    <Badge>{club.status}</Badge>
                  </Group>
                  {club.status === "open" && isAdmin && (
                    <Button mt="sm" size="xs" loading={approveClub.isPending}
                      onClick={() => approveClub.mutate(club.id, {
                        onError: (error) => reportError(error, "Could not confirm club"),
                      })}>
                      Confirm club
                    </Button>
                  )}
                  {club.status === "confirmed" && isStudent && (
                    prior ? <Text size="sm" mt="sm">Membership: {prior.status}</Text> : (
                      <form onSubmit={(event) => applyToClub(event, club)}>
                        <Group align="end" mt="sm">
                          <TextInput name="description" label="Achievements / application" required />
                          <Button type="submit" loading={apply.isPending}>Apply</Button>
                        </Group>
                      </form>
                    )
                  )}
                </Card>
              );
            })}
            {clubsQuery.data?.length === 0 && <Text c="dimmed">No clubs are listed yet.</Text>}
          </Stack>
        </Tabs.Panel>

        {isStudent && (
          <Tabs.Panel value="memberships" pt="md">
            {(membershipsQuery.data ?? []).map((item) => (
              <Card key={item.id} withBorder mb="sm">
                <Group justify="space-between">
                  <Text fw={600}>{item.club_name}</Text><Badge>{item.status}</Badge>
                </Group>
                <Text size="sm">{item.description}</Text>
                {item.remarks && <Text size="sm" c="dimmed">Remarks: {item.remarks}</Text>}
              </Card>
            ))}
            {membershipsQuery.data?.length === 0 && (
              <Text c="dimmed">You have no membership applications.</Text>
            )}
          </Tabs.Panel>
        )}

        {isStudent && (
          <Tabs.Panel value="polls" pt="md">
            {(pollsQuery.data ?? []).map((poll) => (
              <Card key={poll.id} withBorder mb="sm">
                <Text fw={600}>{poll.title}</Text>
                <Text size="sm">{poll.description}</Text>
                <Text size="xs" c="dimmed">Closes {new Date(poll.expires_at).toLocaleString()}</Text>
                <Group mt="sm">
                  {poll.choices.map((choice) => (
                    <Button key={choice.id} variant={poll.has_voted ? "light" : "filled"}
                      disabled={poll.has_voted || vote.isPending}
                      onClick={() => vote.mutate(
                        { pollId: poll.id, choiceId: choice.id },
                        { onError: (error) => reportError(error, "Could not record vote") },
                      )}>
                      {choice.text}{poll.has_voted ? ` · ${choice.vote_count}` : ""}
                    </Button>
                  ))}
                </Group>
              </Card>
            ))}
            {pollsQuery.data?.length === 0 && <Text c="dimmed">No active polls are available to you.</Text>}
          </Tabs.Panel>
        )}

        {myClubs.length > 0 && (
          <Tabs.Panel value="manage" pt="md">
            <Select
              label="Club"
              data={myClubs.map((club) => ({ value: String(club.id), label: club.name }))}
              value={String(selectedClub?.id ?? "")}
              onChange={setSelectedId}
              mb="md"
            />
            {selectedClub && (
              <Tabs defaultValue="schedule">
                <Tabs.List>
                  <Tabs.Tab value="schedule">Sessions & events</Tabs.Tab>
                  <Tabs.Tab value="members">Membership</Tabs.Tab>
                  <Tabs.Tab value="poll">Polls</Tabs.Tab>
                  <Tabs.Tab value="budget">Budget</Tabs.Tab>
                  <Tabs.Tab value="report">Event reports</Tabs.Tab>
                  <Tabs.Tab value="leadership">Leadership</Tabs.Tab>
                </Tabs.List>

                <Tabs.Panel value="schedule" pt="md">
                  <Group grow align="flex-start">
                    <Card withBorder>
                      <Text fw={600} mb="sm">Book a session</Text>
                      <form onSubmit={(event) => submitUpload(event, (data) =>
                        createSession.mutate(
                          { clubId: selectedClub.id, data },
                          uploadCallbacks("Session booked"),
                        ))}>
                        <Stack>
                          <Select name="venue" label="Venue" data={venuesQuery.data ?? []} required />
                          <TextInput name="date" label="Date" type="date" required />
                          <Group grow>
                            <TextInput name="start_time" label="Start" type="time" required />
                            <TextInput name="end_time" label="End" type="time" required />
                          </Group>
                          <Textarea name="description" label="Description" required />
                          <FileInput name="poster" label="Poster (optional)" />
                          <Button type="submit" loading={createSession.isPending}>Book session</Button>
                        </Stack>
                      </form>
                      {(sessions.data ?? []).map((item) => (
                        <Text key={item.id} size="sm" mt="sm">
                          {item.date} {item.start_time}-{item.end_time}, {item.venue}
                          {item.poster_url && <> · <a href={item.poster_url}>Poster</a></>}
                        </Text>
                      ))}
                    </Card>
                    <Card withBorder>
                      <Text fw={600} mb="sm">Book an event</Text>
                      <form onSubmit={(event) => submitUpload(event, (data) =>
                        createEvent.mutate(
                          { clubId: selectedClub.id, data },
                          uploadCallbacks("Event booked"),
                        ))}>
                        <Stack>
                          <TextInput name="name" label="Event name" required />
                          <PersonPicker kind="faculty" name="faculty_user_id"
                            label="Faculty context" />
                          <Select name="venue" label="Venue" data={venuesQuery.data ?? []} required />
                          <TextInput name="date" label="Date" type="date" required />
                          <Group grow>
                            <TextInput name="start_time" label="Start" type="time" required />
                            <TextInput name="end_time" label="End" type="time" required />
                          </Group>
                          <Textarea name="description" label="Description" required />
                          <FileInput name="poster" label="Poster (optional)" />
                          <Button type="submit" loading={createEvent.isPending}>Book event</Button>
                        </Stack>
                      </form>
                      {(events.data ?? []).map((item) => (
                        <Text key={item.id} size="sm" mt="sm">
                          {item.name} · {item.date} · {item.venue}
                          {item.poster_url && <> · <a href={item.poster_url}>Poster</a></>}
                        </Text>
                      ))}
                    </Card>
                  </Group>
                </Tabs.Panel>

                <Tabs.Panel value="members" pt="md">
                  {(clubApplications.data ?? []).map((application) => (
                    <Card key={application.id} withBorder mb="sm">
                      <Group justify="space-between">
                        <div>
                          <Text fw={600}>Student {application.student_user_id}</Text>
                          <Text size="sm">{application.description}</Text>
                        </div>
                        <Button size="xs" loading={approveMembership.isPending}
                          onClick={() => approveApplication(selectedClub.id, application.id)}>
                          Approve
                        </Button>
                      </Group>
                    </Card>
                  ))}
                  {clubApplications.data?.length === 0 && <Text c="dimmed">No open applications.</Text>}
                </Tabs.Panel>

                <Tabs.Panel value="poll" pt="md">
                  <Card withBorder>
                    <form onSubmit={submitPoll}>
                      <Stack>
                        <TextInput name="title" label="Poll title" required />
                        <Textarea name="description" label="Description" />
                        <TextInput name="expires_at" label="Expires at" type="datetime-local" required />
                        <Textarea name="choices" label="Choices (one per line)" minRows={2} required />
                        <Textarea
                          name="target_groups"
                          label="Target groups (one batch year,discipline per line; use * for all branches)"
                          placeholder={"2024,CSE\n2025,*"}
                          minRows={2}
                          required
                        />
                        <Button type="submit" loading={createPoll.isPending}>Create poll</Button>
                      </Stack>
                    </form>
                  </Card>
                </Tabs.Panel>

                <Tabs.Panel value="budget" pt="md">
                  <Card withBorder>
                    <form onSubmit={(event) => submitUpload(event, (data) =>
                      createBudget.mutate(
                        { clubId: selectedClub.id, data },
                        uploadCallbacks("Budget request submitted"),
                      ))}>
                      <Stack>
                        <NumberInput name="amount" label="Amount" min={0} decimalScale={2} required />
                        <TextInput name="purpose" label="Purpose" required />
                        <Textarea name="description" label="Description" required />
                        <FileInput name="supporting_file" label="Supporting file" required />
                        <Button type="submit" loading={createBudget.isPending}>Submit request</Button>
                      </Stack>
                    </form>
                  </Card>
                  {(budgets.data ?? []).map((item) => (
                    <Card key={item.id} withBorder mt="sm">
                      <Group justify="space-between">
                        <Text>{item.purpose} · {item.amount} · {item.status}</Text>
                        <a href={item.download_url}>Supporting file</a>
                      </Group>
                    </Card>
                  ))}
                </Tabs.Panel>

                <Tabs.Panel value="report" pt="md">
                  <Card withBorder>
                    <form onSubmit={(event) => submitUpload(event, (data) =>
                      createReport.mutate(
                        { clubId: selectedClub.id, data },
                        uploadCallbacks("Event report submitted"),
                      ))}>
                      <Stack>
                        <PersonPicker kind="student" name="student_incharge_user_id"
                          label="Student incharge" />
                        <TextInput name="event_name" label="Event name" required />
                        <TextInput name="event_at" label="Event date/time" type="datetime-local" required />
                        <Textarea name="description" label="Description" required />
                        <FileInput name="report_file" label="Report/details file" required />
                        <Button type="submit" loading={createReport.isPending}>Submit report</Button>
                      </Stack>
                    </form>
                  </Card>
                  {(reports.data ?? []).map((report) => (
                    <Card key={report.id} withBorder mt="sm">
                      <Group justify="space-between">
                        <Text>{report.event_name}</Text><a href={report.download_url}>Report file</a>
                      </Group>
                    </Card>
                  ))}
                </Tabs.Panel>

                <Tabs.Panel value="leadership" pt="md">
                  <Card withBorder>
                    <form onSubmit={submitLeadership}>
                      <Stack>
                        <PersonPicker kind="student" name="coordinator_user_id"
                          label="New coordinator" />
                        <PersonPicker kind="student" name="co_coordinator_user_id"
                          label="New co-coordinator" />
                        <Button type="submit" loading={changeLeadership.isPending}>Replace leaders</Button>
                      </Stack>
                    </form>
                  </Card>
                </Tabs.Panel>
              </Tabs>
            )}
          </Tabs.Panel>
        )}

        {isFacultyReviewer && (
          <Tabs.Panel value="reports" pt="md">
            {(assignedReportsQuery.data ?? []).map((report) => (
              <Card key={report.id} withBorder mb="sm">
                <Group justify="space-between">
                  <div>
                    <Text fw={600}>{report.event_name} · {report.club_name}</Text>
                    <Text size="sm">{report.description}</Text>
                  </div>
                  <a href={report.download_url}>Review report</a>
                </Group>
              </Card>
            ))}
            {assignedReportsQuery.data?.length === 0 && (
              <Text c="dimmed">No event reports are assigned to you.</Text>
            )}
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  );
}
