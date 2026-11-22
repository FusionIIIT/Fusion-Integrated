import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Tabs,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaCoins, FaPlaneDeparture } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCpdaClaims,
  useDecideCpda,
  useDecideLeave,
  useDecideLtc,
  useLeaves,
  useLtcClaims,
} from "../api/hooks";
import type { CpdaRequest, LeaveRequest, LtcRequest } from "../api/types";

export default function ApprovalsPage() {
  const { data: leaves, isPending: leavesLoading, error: leavesError } = useLeaves();
  const { data: ltcClaims, isPending: ltcLoading, error: ltcError } = useLtcClaims();
  const { data: cpdaClaims, isPending: cpdaLoading, error: cpdaError } = useCpdaClaims();

  const decideLeave = useDecideLeave();
  const decideLtc = useDecideLtc();
  const decideCpda = useDecideCpda();

  const [activeTab, setActiveTab] = useState<string | null>("leaves");

  // Decision Modal state
  const [modalType, setModalType] = useState<"leave" | "ltc" | "cpda" | null>(null);
  const [targetId, setTargetId] = useState<number | null>(null);
  const [outcome, setOutcome] = useState<string>("approved");
  const [remarks, setRemarks] = useState<string>("");

  if (leavesError || ltcError || cpdaError) {
    return (
      <Container size="xl">
        <ErrorState error={leavesError || ltcError || cpdaError} />
      </Container>
    );
  }

  // Filter pending items
  const pendingLeaves = (leaves ?? []).filter((l) => ["pending", "forwarded"].includes(l.status));
  const pendingLtc = (ltcClaims ?? []).filter((l) => ["verified", "forwarded"].includes(l.status));
  const pendingCpda = (cpdaClaims ?? []).filter((c) => ["verified", "forwarded"].includes(c.status));

  const handleDecision = () => {
    if (!targetId || !modalType) return;

    if (outcome !== "approved" && !remarks) {
      notifications.show({
        title: "Remarks Required",
        message: "Please state remarks when rejecting or forwarding a request.",
        color: "red",
      });
      return;
    }

    const callback = {
      onSuccess: () => {
        notifications.show({
          title: "Decision Recorded",
          message: `Request successfully ${outcome}.`,
          color: "teal",
        });
        setModalType(null);
        setTargetId(null);
        setRemarks("");
      },
      onError: (err: unknown) => {
        notifications.show({
          title: "Error Recording Decision",
          message: errorMessage(err),
          color: "red",
        });
      },
    };

    if (modalType === "leave") {
      decideLeave.mutate({ id: targetId, outcome, remarks }, callback);
    } else if (modalType === "ltc") {
      decideLtc.mutate({ id: targetId, outcome, remarks }, callback);
    } else if (modalType === "cpda") {
      decideCpda.mutate({ id: targetId, outcome, remarks }, callback);
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Pending Approvals & Workflow Queue"
        subtitle="Review, approve, reject, or forward employee requests (BR-HR-009, BR-HR-023)"
      />

      <Tabs value={activeTab} onChange={setActiveTab} radius="md">
        <Tabs.List mb="lg">
          <Tabs.Tab
            value="leaves"
            leftSection={<FaCalendarAlt size={14} />}
            rightSection={<Badge size="xs" color="blue">{pendingLeaves.length}</Badge>}
          >
            Leave Requests
          </Tabs.Tab>
          <Tabs.Tab
            value="ltc"
            leftSection={<FaPlaneDeparture size={14} />}
            rightSection={<Badge size="xs" color="orange">{pendingLtc.length}</Badge>}
          >
            LTC Claims
          </Tabs.Tab>
          <Tabs.Tab
            value="cpda"
            leftSection={<FaCoins size={14} />}
            rightSection={<Badge size="xs" color="grape">{pendingCpda.length}</Badge>}
          >
            CPDA Allowances
          </Tabs.Tab>
        </Tabs.List>

        {/* Leaves Tab */}
        <Tabs.Panel value="leaves">
          <Card withBorder padding="lg" radius="md">
            <DataTable<LeaveRequest>
              rows={pendingLeaves}
              loading={leavesLoading}
              rowKey={(r) => r.id}
              minWidth={800}
              empty={{
                icon: FaCalendarAlt,
                title: "No pending leave applications",
                description: "There are no leave requests currently awaiting your approval.",
              }}
              columns={[
                {
                  key: "user_id",
                  header: "Applicant User",
                  render: (r) => <Text size="sm" fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "type",
                  header: "Leave Type",
                  render: (r) => <Text size="sm" tt="capitalize">{r.leave_type}</Text>,
                },
                {
                  key: "duration",
                  header: "Dates",
                  render: (r) => (
                    <Text size="sm">
                      {r.start_date} to {r.end_date} ({r.duration_days} d)
                    </Text>
                  ),
                },
                {
                  key: "justification",
                  header: "Justification",
                  render: (r) => <Text size="sm" lineClamp={1}>{r.justification}</Text>,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => <StatusBadge status={r.status} />,
                },
                {
                  key: "actions",
                  header: "Action",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="blue"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("leave");
                        setOutcome("approved");
                      }}
                    >
                      Review & Decide
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        {/* LTC Tab */}
        <Tabs.Panel value="ltc">
          <Card withBorder padding="lg" radius="md">
            <DataTable<LtcRequest>
              rows={pendingLtc}
              loading={ltcLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                icon: FaPlaneDeparture,
                title: "No pending LTC claims",
                description: "There are no verified LTC claims waiting for final approval.",
              }}
              columns={[
                {
                  key: "user_id",
                  header: "Employee",
                  render: (r) => <Text size="sm" fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "type",
                  header: "Claim Type",
                  render: (r) => <Badge variant="light">{r.request_type.toUpperCase()}</Badge>,
                },
                {
                  key: "journey",
                  header: "Route",
                  render: (r) => <Text size="sm">{r.travel_from} &rarr; {r.travel_to}</Text>,
                },
                {
                  key: "amount",
                  header: "Amount",
                  render: (r) => <Text size="sm" fw={700}>₹{Number(r.estimated_amount).toLocaleString("en-IN")}</Text>,
                },
                {
                  key: "verification",
                  header: "HR Verification",
                  render: (r) => <StatusBadge status={r.verification_status} />,
                },
                {
                  key: "actions",
                  header: "Action",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="orange"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("ltc");
                        setOutcome("approved");
                      }}
                    >
                      Review & Decide
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        {/* CPDA Tab */}
        <Tabs.Panel value="cpda">
          <Card withBorder padding="lg" radius="md">
            <DataTable<CpdaRequest>
              rows={pendingCpda}
              loading={cpdaLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                icon: FaCoins,
                title: "No pending CPDA claims",
                description: "There are no verified CPDA claims waiting for approval.",
              }}
              columns={[
                {
                  key: "user_id",
                  header: "Faculty User",
                  render: (r) => <Text size="sm" fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "purpose",
                  header: "Purpose",
                  render: (r) => <Text size="sm" lineClamp={1}>{r.purpose}</Text>,
                },
                {
                  key: "amount",
                  header: "Amount",
                  render: (r) => <Text size="sm" fw={700}>₹{Number(r.amount).toLocaleString("en-IN")}</Text>,
                },
                {
                  key: "verification",
                  header: "HR Verification",
                  render: (r) => <StatusBadge status={r.verification_status} />,
                },
                {
                  key: "actions",
                  header: "Action",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="grape"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("cpda");
                        setOutcome("approved");
                      }}
                    >
                      Review & Decide
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Decision Modal */}
      <Modal
        opened={modalType != null}
        onClose={() => setModalType(null)}
        title="Approving Authority Decision"
        size="md"
      >
        <Stack gap="md">
          <Select
            label="Decision Outcome"
            required
            value={outcome}
            onChange={(v) => v && setOutcome(v)}
            data={[
              { value: "approved", label: "Approve Request" },
              { value: "forwarded", label: "Forward to Higher Authority" },
              { value: "rejected", label: "Reject Request" },
            ]}
          />

          <Textarea
            label="Approval Remarks & Justification"
            placeholder="Required if rejecting or forwarding..."
            rows={3}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalType(null)}>
              Cancel
            </Button>
            <Button
              color={outcome === "rejected" ? "red" : outcome === "forwarded" ? "cyan" : "teal"}
              loading={decideLeave.isPending || decideLtc.isPending || decideCpda.isPending}
              onClick={handleDecision}
            >
              Confirm Decision
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
