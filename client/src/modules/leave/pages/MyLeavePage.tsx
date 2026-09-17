import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, SimpleGrid, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory, FaRegCalendarCheck } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { PeriodCell } from "../components/PeriodCell";
import { ResumptionModal } from "../components/ResumptionModal";
import { StateBadge } from "../components/StateBadge";
import { TrailDrawer } from "../components/TrailDrawer";
import {
  useMyBalances, useMyLeave, useRequestCancellation, useWithdraw,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";

/** Withdraw before approval; after it, cancellation is somebody else's decision. */
const WITHDRAWABLE = new Set([
  "AWAITING_SUBSTITUTE", "APPLICANT_ACTION_REQUIRED", "AWAITING_UNIT_HEAD",
  "AWAITING_ESTABLISHMENT", "AWAITING_FINAL_SANCTION", "AWAITING_SELF_SANCTION",
]);
const CANCELLABLE = new Set(["APPROVED_NOT_STARTED"]);
const RESUMABLE = new Set(["ONGOING", "AWAITING_RESUMPTION"]);

export default function MyLeavePage() {
  const navigate = useNavigate();
  const { data, isPending, error } = useMyLeave();
  const balances = useMyBalances();
  const withdraw = useWithdraw();
  const cancel = useRequestCancellation();
  const [trailFor, setTrailFor] = useState<number | null>(null);
  const [resuming, setResuming] = useState<LeaveRequest | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function act(
    run: Promise<unknown>, title: string, message: string,
  ) {
    run
      .then(() => notifications.show({ color: "gray", title, message }))
      .catch((e) => notifications.show({
        color: "red", title: "Not recorded", message: errorMessage(e),
      }));
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Everything you have applied for, and where each request stands"
        action={<Button onClick={() => navigate("apply")}>Apply for leave</Button>}
      />

      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} mb="lg">
        {(balances.data ?? []).map((b) => (
          <Card key={b.category} padding="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{b.category}</Text>
            <Text fw={700} size="xl">{b.available}</Text>
            <Text size="xs" c="dimmed">available</Text>
          </Card>
        ))}
      </SimpleGrid>

      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={data ?? []} loading={isPending} rowKey={(r) => r.id} minWidth={900}
          columns={[
            { key: "category", header: "Type", render: (r) => r.category },
            { key: "period", header: "Period",
              render: (r) => <PeriodCell request={r} /> },
            { key: "reason", header: "Reason",
              render: (r) => <Text size="sm" lineClamp={2}>{r.reason}</Text> },
            { key: "state", header: "Status",
              render: (r) => <StateBadge state={r.state} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <ActionIcon
                    variant="subtle" color="gray" aria-label="History"
                    onClick={() => setTrailFor(r.id)}
                  >
                    <FaHistory size={12} />
                  </ActionIcon>
                  {WITHDRAWABLE.has(r.state) && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={withdraw.isPending}
                      onClick={() => act(
                        withdraw.mutateAsync({ id: r.id }),
                        "Withdrawn",
                        "Your request has been withdrawn.",
                      )}
                    >
                      Withdraw
                    </Button>
                  )}
                  {CANCELLABLE.has(r.state) && (
                    <Button
                      size="xs" variant="subtle" color="orange"
                      loading={cancel.isPending}
                      onClick={() => act(
                        cancel.mutateAsync({ id: r.id }),
                        "Cancellation requested",
                        "Approved leave is cancelled by the same authority that granted it.",
                      )}
                    >
                      Request cancellation
                    </Button>
                  )}
                  {RESUMABLE.has(r.state) && (
                    <Button size="xs" onClick={() => setResuming(r)}>
                      Report resumption
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaRegCalendarCheck,
            title: "You have not applied for any leave",
            description: "Requests you submit are tracked here from start to closure.",
          }}
        />
      </Card>

      <Stack gap={0} mt="md">
        <Text size="xs" c="dimmed">
          A balance shown here is the sum of your leave account entries, not a
          stored figure. Open a category on the Balances screen to see the rows
          behind it.
        </Text>
      </Stack>

      <TrailDrawer requestId={trailFor} onClose={() => setTrailFor(null)} />
      <ResumptionModal request={resuming} onClose={() => setResuming(null)} />
    </Container>
  );
}
