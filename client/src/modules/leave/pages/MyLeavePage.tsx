import { useState } from "react";
import {
  Badge, Button, Card, Container, Grid, Group, Modal, Select, SimpleGrid,
  Stack, Table, Text, Textarea, TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck, FaClipboardCheck, FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useApplyLeave, useLeaveSummary, useMyLeaveRequests, useMySubstitutions,
  useNominateReplacement, useRequestCancellation, useRequestExtension,
  useRespondToSubstitution, useSubmitResumption, useValidateLeave, useWithdraw,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { CATEGORY_LABELS } from "../api/types";

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS)
  .map(([value, label]) => ({ value, label }));

const HALF_OPTIONS = [
  { value: "", label: "Full day" },
  { value: "first", label: "First half" },
  { value: "second", label: "Second half" },
];

/** EL-UC-001: one application, validated before it is allowed to progress. */
function ApplyModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [category, setCategory] = useState<string>("cl");
  const [half, setHalf] = useState<string>("");
  const [from, setFrom] = useState<string | null>(null);
  const [to, setTo] = useState<string | null>(null);
  const [purpose, setPurpose] = useState("");
  const [substitute, setSubstitute] = useState("");
  const [station, setStation] = useState("");
  const [verdict, setVerdict] = useState<{ is_valid: boolean } | null>(null);

  const validate = useValidateLeave();
  const apply = useApplyLeave();

  function reset() {
    setVerdict(null);
    setPurpose("");
    setStation("");
    setSubstitute("");
  }

  const body = {
    category,
    period_from: from ?? "",
    period_to: to ?? from ?? "",
    half,
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Apply for leave" size="lg">
      <Stack>
        <Select
          label="Leave category" data={CATEGORY_OPTIONS} value={category}
          onChange={(v) => { setCategory(v ?? "cl"); reset(); }} allowDeselect={false}
        />
        <Group grow>
          <DateInput label="From" value={from ?? undefined} onChange={setFrom} />
          <DateInput label="To" value={to ?? undefined} onChange={setTo} />
        </Group>
        {category === "cl" && (
          <Select
            label="Half day" data={HALF_OPTIONS} value={half}
            onChange={(v) => { setHalf(v ?? ""); reset(); }} allowDeselect={false}
          />
        )}
        <Textarea
          label="Purpose / reason" minRows={2} value={purpose}
          onChange={(e) => setPurpose(e.currentTarget.value)}
        />
        <TextInput
          label="Substitute employee id" description="Only when responsibility coverage is required"
          value={substitute} onChange={(e) => setSubstitute(e.currentTarget.value)}
        />
        <Textarea
          label="Station leave details" minRows={2}
          description="Captured inside this application, not as a separate request"
          value={station} onChange={(e) => setStation(e.currentTarget.value)}
        />

        {verdict && (
          <Card withBorder padding="sm" bg={verdict.is_valid ? "green.0" : "red.0"}>
            <Stack gap={4}>
              <Text size="sm" fw={600}>
                Check the server result for whether this application can proceed.
              </Text>
            </Stack>
          </Card>
        )}

        <Group justify="flex-end">
          <Button
            variant="default" loading={validate.isPending}
            disabled={!from}
            onClick={() => validate.mutate(body, {
              onSuccess: (data) => setVerdict(data as { is_valid: boolean }),
              onError: (e) => notifications.show({
                color: "red", title: "Could not validate", message: errorMessage(e),
              }),
            })}
          >
            Check
          </Button>
          <Button
            loading={apply.isPending}
            disabled={!from || (verdict ? !verdict.is_valid : false)}
            onClick={() => apply.mutate({
              ...body,
              purpose,
              substitute_user_id: substitute ? Number(substitute) : null,
              station_leave: station ? { details: station } : undefined,
            }, {
              onSuccess: () => {
                notifications.show({
                  color: "green", title: "Submitted",
                  message: "Your request has entered the applicable processing path.",
                });
                reset();
                onClose();
              },
              onError: (e) => notifications.show({
                color: "red", title: "Could not submit", message: errorMessage(e),
              }),
            })}
          >
            Submit
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export default function MyLeavePage() {
  const summary = useLeaveSummary();
  const requests = useMyLeaveRequests();
  const substitutions = useMySubstitutions();
  const respond = useRespondToSubstitution();
  const withdraw = useWithdraw();
  const cancel = useRequestCancellation();
  const extend = useRequestExtension();
  const resume = useSubmitResumption();
  const nominate = useNominateReplacement();
  const [applying, setApplying] = useState(false);
  const [replacementFor, setReplacementFor] = useState<number | null>(null);
  const [replacementId, setReplacementId] = useState("");
  const [extensionFor, setExtensionFor] = useState<number | null>(null);
  const [extensionTo, setExtensionTo] = useState<string | null>(null);
  const [resumeFor, setResumeFor] = useState<number | null>(null);
  const [resumeDate, setResumeDate] = useState<string | null>(null);

  if (summary.error) {
    return <Container size="xl"><ErrorState error={summary.error} /></Container>;
  }

  function act(fn: () => void, title: string) {
    fn();
    notifications.show({ color: "blue", title, message: "The request has been updated." });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Balances, your requests, and anything waiting on you as a substitute"
        action={<Button leftSection={<FaCalendarCheck size={12} />}
                        onClick={() => setApplying(true)}>Apply for leave</Button>}
      />

      <SimpleGrid cols={{ base: 2, md: 4 }} mb="lg">
        {(summary.data?.balances ?? []).map((b) => (
          <Card key={b.id} withBorder padding="md">
            <Text size="xs" c="dimmed" tt="uppercase">{b.category_label}</Text>
            <Text fw={700} size="xl">{b.available_days}</Text>
            <Text size="xs" c="dimmed">
              {b.used_days} used of {b.entitled_days}
              {Number(b.carried_days) > 0 ? ` + ${b.carried_days} carried` : ""}
            </Text>
          </Card>
        ))}
        {(summary.data?.balances ?? []).length === 0 && !summary.isPending && (
          <Card withBorder padding="md">
            <Text size="sm" c="dimmed">No leave account yet for this year.</Text>
          </Card>
        )}
      </SimpleGrid>

      <Grid>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card withBorder padding="lg">
            <Text fw={600} mb="sm">My requests</Text>
            <DataTable<LeaveRequest>
              rows={(requests.data?.results ?? [])}
              loading={requests.isPending}
              rowKey={(r) => r.id}
              minWidth={760}
              columns={[
                { key: "reference", header: "Reference",
                  render: (r) => <Text size="sm">{r.reference ?? `#${r.id}`}</Text> },
                { key: "category", header: "Category",
                  render: (r) => (
                    <Stack gap={0}>
                      <Text size="sm" fw={500}>{r.category_label}</Text>
                      <Text size="xs" c="dimmed">{r.kind_label}</Text>
                    </Stack>
                  ) },
                { key: "period", header: "Period",
                  render: (r) => (
                    <Text size="sm">
                      {r.period_from} → {r.period_to}
                      {r.half ? ` (${r.half} half)` : ""}
                    </Text>
                  ) },
                { key: "days", header: "Days", render: (r) => r.days_counted },
                { key: "status", header: "Status",
                  render: (r) => <StatusBadge status={r.status} /> },
                {
                  key: "actions", header: "", align: "right",
                  render: (r) => (
                    <Group justify="flex-end" gap={4} wrap="nowrap">
                      <Button
                        size="compact-xs" variant="subtle"
                        component="a" target="_blank" rel="noopener"
                        href={`/api/v1/leave/requests/${r.id}/print`}
                      >
                        Print
                      </Button>
                      {r.is_pending && (
                        <Button
                          size="compact-xs" variant="subtle" color="gray"
                          loading={withdraw.isPending}
                          onClick={() => act(
                            () => withdraw.mutate({ id: r.id, reason: "Withdrawn by the employee" }),
                            "Withdrawn")}
                        >
                          Withdraw
                        </Button>
                      )}
                      {(r.status === "approved" || r.status === "extended") && (
                        <>
                          <Button
                            size="compact-xs" variant="subtle" color="gray"
                            onClick={() => { setExtensionFor(r.id); setExtensionTo(null); }}
                          >
                            Extend
                          </Button>
                          <Button
                            size="compact-xs" variant="subtle" color="gray"
                            onClick={() => { setResumeFor(r.id); setResumeDate(null); }}
                          >
                            Resume
                          </Button>
                          <Button
                            size="compact-xs" variant="subtle" color="red"
                            loading={cancel.isPending}
                            onClick={() => act(
                              () => cancel.mutate({ id: r.id, note: "Cancellation requested" }),
                              "Cancellation requested")}
                          >
                            Cancel
                          </Button>
                        </>
                      )}
                      {r.status === "applicant_action_required"
                        || r.status === "extension_applicant_action_required" ? (
                          <Button
                            size="compact-xs" variant="subtle"
                            onClick={() => { setReplacementFor(r.id); setReplacementId(""); }}
                          >
                            Replace substitute
                          </Button>
                        ) : null}
                    </Group>
                  ),
                },
              ]}
              empty={{ icon: FaClipboardCheck, title: "No leave requests yet", description: "Applications you submit appear here with their status." }}
            />
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card withBorder padding="lg">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Responsibility requests</Text>
              <Badge variant="light">
                {summary.data?.substitutions_awaiting_response ?? 0} awaiting you
              </Badge>
            </Group>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Applicant</Table.Th>
                  <Table.Th>Period</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(substitutions.data?.results ?? [])
                  .filter((a) => a.status === "nominated")
                  .map((a) => (
                    <Table.Tr key={a.id}>
                      <Table.Td>u{a.applicant_user_id}</Table.Td>
                      <Table.Td>
                        <Text size="sm">{a.period_from} → {a.period_to}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={4} justify="flex-end">
                          <Button
                            size="compact-xs" variant="light" loading={respond.isPending}
                            onClick={() => respond.mutate({ id: a.id, accept: true }, {
                              onSuccess: () => notifications.show({
                                color: "green", title: "Accepted",
                                message: "The request proceeds to Unit Head review.",
                              }),
                              onError: (e) => notifications.show({
                                color: "red", title: "Could not respond",
                                message: errorMessage(e),
                              }),
                            })}
                          >
                            Accept
                          </Button>
                          <Button
                            size="compact-xs" variant="subtle" color="red"
                            onClick={() => respond.mutate({ id: a.id, accept: false }, {
                              onSuccess: () => notifications.show({
                                color: "orange", title: "Declined",
                                message: "The applicant may nominate a replacement.",
                              }),
                              onError: (e) => notifications.show({
                                color: "red", title: "Could not respond",
                                message: errorMessage(e),
                              }),
                            })}
                          >
                            Decline
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
              </Table.Tbody>
            </Table>
            {(substitutions.data?.results ?? []).length === 0 && (
              <Text size="sm" c="dimmed">
                <FaUserCheck size={12} /> Nothing is waiting on you.
              </Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>

      <ApplyModal opened={applying} onClose={() => setApplying(false)} />

      <Modal opened={replacementFor !== null} onClose={() => setReplacementFor(null)}
             title="Nominate a replacement substitute">
        <Stack>
          <TextInput
            label="Employee id" value={replacementId}
            onChange={(e) => setReplacementId(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button
              loading={nominate.isPending}
              disabled={!replacementId}
              onClick={() => nominate.mutate(
                { id: replacementFor!, substitute_user_id: Number(replacementId) },
                {
                  onSuccess: () => {
                    notifications.show({
                      color: "green", title: "Nominated",
                      message: "The replacement's consent is awaited.",
                    });
                    setReplacementFor(null);
                  },
                  onError: (e) => notifications.show({
                    color: "red", title: "Could not nominate", message: errorMessage(e),
                  }),
                })}
            >
              Nominate
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={extensionFor !== null} onClose={() => setExtensionFor(null)}
             title="Request an extension">
        <Stack>
          <Text size="sm" c="dimmed">
            Only the additional period is posted if the extension is approved.
          </Text>
          <DateInput label="Extend until" value={extensionTo ?? undefined} onChange={setExtensionTo} />
          <Group justify="flex-end">
            <Button
              loading={extend.isPending} disabled={!extensionTo}
              onClick={() => extend.mutate(
                { id: extensionFor!, period_to: extensionTo! }, {
                  onSuccess: () => {
                    notifications.show({
                      color: "green", title: "Extension submitted",
                      message: "It follows the applicable sanction path.",
                    });
                    setExtensionFor(null);
                  },
                  onError: (e) => notifications.show({
                    color: "red", title: "Could not request", message: errorMessage(e),
                  }),
                })}
            >
              Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={resumeFor !== null} onClose={() => setResumeFor(null)}
             title="Submit resumption of duty">
        <Stack>
          <Text size="sm" c="dimmed">
            The Sanctioning Authority reviews this; a balance adjustment happens
            only if the return date differs from the approved end date.
          </Text>
          <DateInput label="Actual resumption date" value={resumeDate ?? undefined} onChange={setResumeDate} />
          <Group justify="flex-end">
            <Button
              loading={resume.isPending} disabled={!resumeDate}
              onClick={() => resume.mutate(
                { id: resumeFor!, actual_date: resumeDate! }, {
                  onSuccess: () => {
                    notifications.show({
                      color: "green", title: "Submitted for review",
                      message: "The applicable authority will review it.",
                    });
                    setResumeFor(null);
                  },
                  onError: (e) => notifications.show({
                    color: "red", title: "Could not submit", message: errorMessage(e),
                  }),
                })}
            >
              Submit
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
