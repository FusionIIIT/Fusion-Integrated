import { useState } from "react";
import { Badge, Button, Group, Modal, Stack, Tabs, Text, Textarea } from "@mantine/core";
import { FaCheck, FaTimes } from "react-icons/fa";
import { Column, DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  usePendingApprovals,
  useSanctionDecideMutation,
  useUnitHeadReviewMutation,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function ApprovalsPage() {
  const { data: approvals, isLoading, refetch } = usePendingApprovals();
  const unitHeadMutation = useUnitHeadReviewMutation();
  const sanctionMutation = useSanctionDecideMutation();

  const [decisionModalApp, setDecisionModalApp] = useState<LeaveApplication | null>(null);
  const [decisionType, setDecisionType] = useState<"UNIT_HEAD" | "SANCTION">("UNIT_HEAD");
  const [outcome, setOutcome] = useState<string>("APPROVE");
  const [remarks, setRemarks] = useState("");

  const handleOpenDecision = (app: LeaveApplication, type: "UNIT_HEAD" | "SANCTION", selectedOutcome: string) => {
    setDecisionModalApp(app);
    setDecisionType(type);
    setOutcome(selectedOutcome);
    setRemarks("");
  };

  const handleDecisionSubmit = async () => {
    if (!decisionModalApp) return;

    if (decisionType === "UNIT_HEAD") {
      await unitHeadMutation.mutateAsync({
        applicationId: decisionModalApp.id,
        outcome: outcome as "RECOMMENDED" | "NOT_RECOMMENDED" | "APPROVE" | "REJECT",
        remarks,
      });
    } else {
      await sanctionMutation.mutateAsync({
        applicationId: decisionModalApp.id,
        approve: outcome === "APPROVE",
        remarks,
      });
    }

    setDecisionModalApp(null);
    refetch();
  };

  const columns: Column<LeaveApplication>[] = [
    {
      key: "id",
      header: "ID",
      render: (r) => <Text fw={500}>#{r.id}</Text>,
    },
    {
      key: "employee",
      header: "Employee",
      render: (r) => <Text size="sm">Employee #{r.employee_id}</Text>,
    },
    {
      key: "type",
      header: "Category",
      render: (r) => (
        <Group gap="xs">
          <Badge variant="outline">{r.leave_type_code}</Badge>
          <Text size="sm">{r.leave_type_name}</Text>
        </Group>
      ),
    },
    {
      key: "dates",
      header: "Period",
      render: (r) => <Text size="sm">{r.start_date} to {r.end_date} ({r.days}d)</Text>,
    },
    {
      key: "status",
      header: "Stage",
      render: (r) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "actions",
      header: "Action",
      align: "right",
      render: (r) => {
        const isClRh = ["CL", "RH"].includes(r.leave_type_code);

        if (r.status === "AWAITING_UNIT_HEAD") {
          return (
            <Group gap="xs" justify="flex-end">
              {isClRh ? (
                <>
                  <Button
                    size="xs"
                    color="green"
                    leftSection={<FaCheck size={12} />}
                    onClick={() => handleOpenDecision(r, "UNIT_HEAD", "APPROVE")}
                  >
                    Approve
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="light"
                    leftSection={<FaTimes size={12} />}
                    onClick={() => handleOpenDecision(r, "UNIT_HEAD", "REJECT")}
                  >
                    Reject
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    size="xs"
                    color="blue"
                    onClick={() => handleOpenDecision(r, "UNIT_HEAD", "RECOMMENDED")}
                  >
                    Recommend
                  </Button>
                  <Button
                    size="xs"
                    color="gray"
                    variant="light"
                    onClick={() => handleOpenDecision(r, "UNIT_HEAD", "NOT_RECOMMENDED")}
                  >
                    Not Recommend
                  </Button>
                </>
              )}
            </Group>
          );
        }

        if (r.status === "AWAITING_SANCTION" || r.status === "AWAITING_DIRECTOR_SELF_SANCTION") {
          return (
            <Group gap="xs" justify="flex-end">
              <Button
                size="xs"
                color="green"
                leftSection={<FaCheck size={12} />}
                onClick={() => handleOpenDecision(r, "SANCTION", "APPROVE")}
              >
                Sanction Approve
              </Button>
              <Button
                size="xs"
                color="red"
                variant="light"
                leftSection={<FaTimes size={12} />}
                onClick={() => handleOpenDecision(r, "SANCTION", "REJECT")}
              >
                Reject
              </Button>
            </Group>
          );
        }

        return null;
      },
    },
  ];

  return (
    <div>
      <PageHeader
        title="Leave Approvals & Sanctions"
        subtitle="Review, recommend, and sanction applications across organizational hierarchy"
      />

      <Tabs defaultValue="unit_head">
        <Tabs.List mb="md">
          <Tabs.Tab value="unit_head">
            Unit Head Review ({approvals?.unit_head?.length ?? 0})
          </Tabs.Tab>
          {approvals?.sanction && (
            <Tabs.Tab value="sanction">
              Sanction Authority ({approvals.sanction.length})
            </Tabs.Tab>
          )}
          {approvals?.establishment && (
            <Tabs.Tab value="establishment">
              Establishment ({approvals.establishment.length})
            </Tabs.Tab>
          )}
        </Tabs.List>

        <Tabs.Panel value="unit_head">
          <DataTable
            rows={approvals?.unit_head ?? []}
            columns={columns}
            loading={isLoading}
            rowKey={(r) => r.id}
            empty={{
              title: "No applications awaiting Unit Head review",
              description: "All requests for your department/section have been reviewed.",
            }}
          />
        </Tabs.Panel>

        {approvals?.sanction && (
          <Tabs.Panel value="sanction">
            <DataTable
              rows={approvals.sanction}
              columns={columns}
              loading={isLoading}
              rowKey={(r) => r.id}
              empty={{
                title: "No applications awaiting sanction decision",
                description: "All routed higher-sanction requests have been decided.",
              }}
            />
          </Tabs.Panel>
        )}

        {approvals?.establishment && (
          <Tabs.Panel value="establishment">
            <DataTable
              rows={approvals.establishment}
              columns={columns}
              loading={isLoading}
              rowKey={(r) => r.id}
              empty={{
                title: "No applications awaiting establishment routing",
                description: "All requests have been verified and routed.",
              }}
            />
          </Tabs.Panel>
        )}
      </Tabs>

      <Modal
        opened={Boolean(decisionModalApp)}
        onClose={() => setDecisionModalApp(null)}
        title={`Decision on Application #${decisionModalApp?.id}`}
      >
        <Stack gap="md">
          <Text size="sm">
            Action: <strong>{outcome.replace(/_/g, " ")}</strong> for{" "}
            {decisionModalApp?.leave_type_code} leave ({decisionModalApp?.days} days).
          </Text>
          <Textarea
            label="Decision Remarks / Comments"
            placeholder="Enter reason or comments for this decision..."
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDecisionModalApp(null)}>
              Cancel
            </Button>
            <Button
              color={outcome.includes("REJECT") ? "red" : "blue"}
              onClick={handleDecisionSubmit}
              loading={unitHeadMutation.isPending || sanctionMutation.isPending}
            >
              Confirm Decision
            </Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  );
}
