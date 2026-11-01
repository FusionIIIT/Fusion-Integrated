import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaCreditCard, FaQuestionCircle, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDecideMaintenanceRenewal,
  useMaintenanceSchedules,
  useRequestMaintenanceDecision,
} from "../api/hooks";
import type { MaintenanceSchedule } from "../api/types";
import { MaintenancePaymentModal } from "../components/MaintenancePaymentModal";
import { StatusBadge } from "../components/StatusBadge";

export default function MaintenancePage() {
  const [payModalSchedule, setPayModalSchedule] = useState<MaintenanceSchedule | null>(null);

  const { data, isPending, error } = useMaintenanceSchedules();
  const [activeSchedId, setActiveSchedId] = useState<number | null>(null);

  const requestDecisionMutation = useRequestMaintenanceDecision(activeSchedId ?? 0);
  const decideMutation = useDecideMaintenanceRenewal(activeSchedId ?? 0);

  const handleRequestDecision = async (id: number) => {
    setActiveSchedId(id);
    try {
      await requestDecisionMutation.mutateAsync();
      notifications.show({
        color: "green",
        message: "Renewal decision requested from Director (BR-PMS-061).",
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleDirectorDecide = async (id: number, decision: "renew" | "do_not_renew") => {
    setActiveSchedId(id);
    try {
      await decideMutation.mutateAsync({
        decision,
        justification: decision === "renew" ? "Commercially active patent asset." : "Asset abandoned due to lack of commercial interest.",
      });
      notifications.show({
        color: decision === "renew" ? "teal" : "gray",
        message: `Director renewal determination '${decision}' recorded.`,
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<MaintenanceSchedule>[] = [
    {
      key: "post_grant_id",
      header: "Patent Asset",
      render: (row) => (
        <Text fw={600} size="sm">
          Patent Record #{row.post_grant_id}
        </Text>
      ),
    },
    {
      key: "cycle_year",
      header: "Annuity Year",
      render: (row) => (
        <Text fw={500} size="sm">
          Year {row.cycle_year}
        </Text>
      ),
    },
    {
      key: "fee_amount",
      header: "Statutory Fee",
      render: (row) => (
        <Text size="sm" fw={600}>
          ₹ {row.fee_amount}
        </Text>
      ),
    },
    {
      key: "due_date",
      header: "Due Date",
      render: (row) => (
        <Text size="xs">{row.due_date}</Text>
      ),
    },
    {
      key: "status",
      header: "Renewal Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "payment_record_reference",
      header: "Challan / Payment Ref",
      render: (row) => (
        <Text size="xs" c={row.payment_record_reference ? "teal" : "dimmed"}>
          {row.payment_record_reference || "Unpaid"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Group justify="flex-end" gap="xs">
          {row.status === "scheduled" && (
            <Button
              size="xs"
              variant="light"
              color="orange"
              leftSection={<FaQuestionCircle />}
              onClick={() => handleRequestDecision(row.id)}
              loading={requestDecisionMutation.isPending && activeSchedId === row.id}
            >
              Request Decision
            </Button>
          )}

          {row.status === "decision_requested" && (
            <>
              <Button
                size="xs"
                color="teal"
                leftSection={<FaCheck />}
                onClick={() => handleDirectorDecide(row.id, "renew")}
                loading={decideMutation.isPending && activeSchedId === row.id}
              >
                Renew
              </Button>
              <Button
                size="xs"
                color="red"
                variant="light"
                leftSection={<FaTimes />}
                onClick={() => handleDirectorDecide(row.id, "do_not_renew")}
                loading={decideMutation.isPending && activeSchedId === row.id}
              >
                Abandon
              </Button>
            </>
          )}

          {row.status === "renewal_approved" && (
            <Button
              size="xs"
              color="teal"
              leftSection={<FaCreditCard />}
              onClick={() => setPayModalSchedule(row)}
            >
              Record Payment
            </Button>
          )}
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Post-Grant Maintenance & Annuity Renewals"
        subtitle="20-year patent term lifecycle tracking, institutional renewal decisions, and statutory annuity payments (BR-PMS-059..061)."
      />

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No maintenance schedules",
            description: "No post-grant maintenance schedules active.",
          }}
        />
      </Card>

      <MaintenancePaymentModal
        scheduleId={payModalSchedule?.id ?? null}
        feeAmount={payModalSchedule?.fee_amount ?? "0.00"}
        cycleYear={payModalSchedule?.cycle_year ?? 0}
        opened={payModalSchedule != null}
        onClose={() => setPayModalSchedule(null)}
      />
    </Container>
  );
}
