import { useState } from "react";
import { ActionIcon, Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaHistory, FaInbox } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { LeaveRequest } from "../api/types";
import { DecisionModal } from "./DecisionModal";
import { PeriodCell } from "./PeriodCell";
import { StateBadge } from "./StateBadge";
import { TrailDrawer } from "./TrailDrawer";

interface Props {
  title: string;
  subtitle: string;
  emptyTitle: string;
  emptyDescription: string;
  rows: LeaveRequest[];
  loading: boolean;
  error: unknown;
  approveLabel: string;
  /** Omitted where the queue only forwards, as the establishment step does. */
  refuseLabel?: string;
  submitting?: boolean;
  onDecide: (id: number, approve: boolean, remark: string) => Promise<unknown>;
}

/** The four review queues differ in their heading and in which service call
 *  they make. Everything else — the table, the history drawer, the remark
 *  modal — is identical, and four copies of it would drift apart. */
export function QueuePage({
  title, subtitle, emptyTitle, emptyDescription, rows, loading, error,
  approveLabel, refuseLabel, submitting, onDecide,
}: Props) {
  const [trailFor, setTrailFor] = useState<number | null>(null);
  const [deciding, setDeciding] = useState<
    { request: LeaveRequest; approve: boolean } | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function confirm(remark: string) {
    if (!deciding) return;
    const { request, approve } = deciding;
    onDecide(request.id, approve, remark)
      .then(() => {
        setDeciding(null);
        notifications.show({
          color: approve ? "green" : "gray",
          title: approve ? approveLabel : "Refused",
          message: `${request.category} for ${request.starts_on} has been recorded.`,
        });
      })
      .catch((e) => notifications.show({
        color: "red", title: "Not recorded", message: errorMessage(e),
      }));
  }

  return (
    <Container size="xl">
      <PageHeader title={title} subtitle={subtitle} />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={rows} loading={loading} rowKey={(r) => r.id} minWidth={900}
          columns={[
            { key: "user", header: "Employee", render: (r) => r.user_id },
            { key: "category", header: "Type", render: (r) => r.category },
            { key: "period", header: "Period",
              render: (r) => <PeriodCell request={r} /> },
            { key: "reason", header: "Reason", render: (r) => r.reason },
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
                  {refuseLabel && (
                    <Button
                      size="xs" variant="subtle" color="red"
                      onClick={() => setDeciding({ request: r, approve: false })}
                    >
                      {refuseLabel}
                    </Button>
                  )}
                  <Button
                    size="xs"
                    onClick={() => setDeciding({ request: r, approve: true })}
                  >
                    {approveLabel}
                  </Button>
                </Group>
              ),
            },
          ]}
          empty={{ icon: FaInbox, title: emptyTitle, description: emptyDescription }}
        />
      </Card>

      <DecisionModal
        request={deciding?.request ?? null}
        approve={deciding?.approve ?? true}
        verb={approveLabel}
        submitting={submitting}
        onClose={() => setDeciding(null)}
        onConfirm={confirm}
      />
      <TrailDrawer requestId={trailFor} onClose={() => setTrailFor(null)} />
    </Container>
  );
}
