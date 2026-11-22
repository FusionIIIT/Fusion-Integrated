import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";
import type { SubstituteRequest } from "../api/types";

export default function SubstitutesPage() {
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState<SubstituteRequest[]>([]);
  const [actionReq, setActionReq] = useState<SubstituteRequest | null>(null);
  const [decision, setDecision] = useState<"accepted" | "declined">("accepted");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const data = await leaveApi.getMySubstituteRequests();
      setRequests(data);
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleRespond = async () => {
    if (!actionReq) return;
    try {
      setSubmitting(true);
      await leaveApi.respondToSubstituteRequest(actionReq.id, decision, remarks);
      notifications.show({
        title: "Responsibility Updated",
        message: `Successfully ${decision} substitute request.`,
        color: decision === "accepted" ? "teal" : "orange",
      });
      setActionReq(null);
      setRemarks("");
      fetchRequests();
    } catch (err) {
      notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Substitute Responsibility Requests"
        subtitle="Colleagues who have nominated you to cover their duties during leave."
      />

      <Card padding="lg" shadow="sm" radius="md" withBorder>
        <DataTable<SubstituteRequest>
          rows={requests}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No substitute requests", description: "You have no pending requests to cover duties for colleagues." }}
          columns={[
            { key: "id", header: "Request ID", render: (r) => `#${r.id}` },
            { key: "app", header: "Application", render: (r) => `Leave Application #${r.application_id}` },
            { key: "resp", header: "Responsibilities", render: (r) => r.responsibilities || "General duty coverage" },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Badge color={r.status === "accepted" ? "green" : r.status === "declined" ? "red" : "blue"}>
                  {r.status.toUpperCase()}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group gap="xs">
                  {r.status === "pending" && (
                    <>
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => {
                          setActionReq(r);
                          setDecision("accepted");
                        }}
                      >
                        Accept
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="outline"
                        onClick={() => {
                          setActionReq(r);
                          setDecision("declined");
                        }}
                      >
                        Decline
                      </Button>
                    </>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        opened={!!actionReq}
        onClose={() => setActionReq(null)}
        title={`${decision === "accepted" ? "Accept" : "Decline"} Responsibility`}
      >
        <Stack gap="md">
          <Text size="sm">
            {decision === "accepted"
              ? "Confirming consent allows the applicant's leave to proceed to approval routing."
              : "Declining will notify the applicant to nominate a different substitute or withdraw."}
          </Text>
          <TextInput
            label="Remarks (optional)"
            placeholder="Add any notes..."
            value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setActionReq(null)}>Cancel</Button>
            <Button
              color={decision === "accepted" ? "teal" : "red"}
              loading={submitting}
              onClick={handleRespond}
            >
              Confirm {decision === "accepted" ? "Acceptance" : "Decline"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
