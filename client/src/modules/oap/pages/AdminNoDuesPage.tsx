import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useFinalizeNoDues,
  useNoDues,
  useRecordSignoff,
} from "../api/hooks";
import type { NoDuesRequest } from "../api/types";

const DEPARTMENTS = [
  { value: "LIBRARY", label: "Central Library" },
  { value: "HOSTEL", label: "Hall of Residence" },
  { value: "ACCOUNTS", label: "Accounts & Finance" },
  { value: "SPORTS", label: "Sports Officer / Gymkhana" },
  { value: "LABORATORY", label: "Departmental Laboratories" },
  { value: "DISCIPLINE", label: "Proctorial / Disciplinary Committee" },
];

const STATUSES = [
  { value: "CLEARED", label: "Cleared (No Dues)" },
  { value: "DUES_PENDING", label: "Dues Pending / Fine" },
];

export default function AdminNoDuesPage() {
  const { data, isPending, error } = useNoDues();
  const { can, session } = useAuth();

  const [activeReq, setActiveReq] = useState<NoDuesRequest | null>(null);
  const [modalMode, setModalMode] = useState<"signoff" | "finalize">("signoff");

  const [dept, setDept] = useState("LIBRARY");
  const [signStatus, setSignStatus] = useState("CLEARED");
  const [duesAmount, setDuesAmount] = useState("0.00");
  const [signoffRemarks, setSignoffRemarks] = useState("");
  const [officerId, setOfficerId] = useState(session?.user.username ?? "OFFICER");

  const signoffMutation = useRecordSignoff();
  const finalizeMutation = useFinalizeNoDues();

  const canFinalize = can("oap.nodues.finalize");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading institutional no-dues requests...</Text>
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const requests = data?.results ?? [];

  const handleAction = async () => {
    if (!activeReq) return;
    try {
      if (modalMode === "signoff") {
        await signoffMutation.mutateAsync({
          id: activeReq.id,
          department: dept,
          status: signStatus,
          signoff_by: officerId,
          dues_amount: duesAmount,
          remarks: signoffRemarks,
        });
        notifications.show({
          color: "green",
          title: "Sign-off Recorded",
          message: `Department sign-off recorded for ${dept}.`,
        });
      } else {
        const res = await finalizeMutation.mutateAsync({
          id: activeReq.id,
          finalized_by: officerId,
        });
        if (res.cleared) {
          notifications.show({
            color: "green",
            title: "Clearance Finalized",
            message: `Student ${activeReq.student_id} is fully cleared and certificate issued.`,
          });
        } else {
          notifications.show({
            color: "orange",
            title: "Clearance Incomplete",
            message: "All 6 departmental sign-offs must be CLEARED before final clearance.",
          });
        }
      }
      setActiveReq(null);
      setDuesAmount("0.00");
      setSignoffRemarks("");
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Action Failed",
        message: errorMessage(e),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Institutional No-Dues Management"
        subtitle="Record departmental clearances and issue consolidated institutional no-dues certificates"
      />

      {requests.length === 0 ? (
        <Alert title="No No-Dues Workflows" color="blue" data-testid="empty-state">
          There are no active or past no-dues clearance requests in the system.
        </Alert>
      ) : (
        <Stack gap="lg">
          {requests.map((r) => (
            <Card key={r.id} withBorder radius="md">
              <Group justify="space-between" mb="sm">
                <div>
                  <Title order={4}>
                    Student: {r.student_id} (#{r.id})
                  </Title>
                  <Text size="sm" c="dimmed">
                    Reason: {r.reason} | Initiated: {new Date(r.created_at).toLocaleDateString()}
                  </Text>
                </div>
                <Group>
                  <Badge
                    size="lg"
                    color={r.overall_status === "CLEARED" ? "green" : "blue"}
                  >
                    {r.overall_status}
                  </Badge>
                  {canFinalize && r.overall_status !== "CLEARED" && (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => {
                          setActiveReq(r);
                          setModalMode("signoff");
                        }}
                        aria-label={`Record departmental sign-off for ${r.student_id}`}
                      >
                        Sign-off Dept
                      </Button>
                      <Button
                        size="xs"
                        color="green"
                        onClick={() => {
                          setActiveReq(r);
                          setModalMode("finalize");
                        }}
                        aria-label={`Finalize clearance for ${r.student_id}`}
                      >
                        Finalize Clearance
                      </Button>
                    </Group>
                  )}
                </Group>
              </Group>

              {r.clearance_certificate_number && (
                <Text size="sm" c="green" fw={500} mb="xs">
                  Certificate #: {r.clearance_certificate_number}
                </Text>
              )}

              <Table verticalSpacing="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Department</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Dues Amount</Table.Th>
                    <Table.Th>Officer</Table.Th>
                    <Table.Th>Remarks</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {r.signoffs.map((s) => (
                    <Table.Tr key={s.id}>
                      <Table.Td>{s.department.replace(/_/g, " ")}</Table.Td>
                      <Table.Td>
                        <Badge
                          size="xs"
                          color={
                            s.status === "CLEARED"
                              ? "green"
                              : s.status === "DUES_PENDING"
                                ? "red"
                                : "gray"
                          }
                        >
                          {s.status}
                        </Badge>
                      </Table.Td>
                      <Table.Td>₹{s.dues_amount}</Table.Td>
                      <Table.Td>{s.signoff_by || "—"}</Table.Td>
                      <Table.Td>{s.remarks || "—"}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
          ))}
        </Stack>
      )}

      <FormModal
        opened={activeReq !== null}
        onClose={() => setActiveReq(null)}
        title={
          modalMode === "signoff"
            ? `Record Departmental Sign-off for ${activeReq?.student_id}`
            : `Finalize Consolidated Clearance for ${activeReq?.student_id}`
        }
        submitLabel={modalMode === "signoff" ? "Save Sign-off" : "Confirm Final Clearance"}
        onSubmit={handleAction}
        submitting={signoffMutation.isPending || finalizeMutation.isPending}
      >
        <Stack gap="md">
          <TextInput
            label="Officer ID"
            value={officerId}
            onChange={(e) => setOfficerId(e.currentTarget.value)}
            required
            aria-label="Officer ID"
          />
          {modalMode === "signoff" ? (
            <>
              <Select
                label="Department"
                data={DEPARTMENTS}
                value={dept}
                onChange={(val) => setDept(val ?? "LIBRARY")}
                required
                aria-label="Department"
              />
              <Select
                label="Clearance Status"
                data={STATUSES}
                value={signStatus}
                onChange={(val) => setSignStatus(val ?? "CLEARED")}
                required
                aria-label="Clearance Status"
              />
              <TextInput
                label="Outstanding Dues Amount (₹)"
                value={duesAmount}
                onChange={(e) => setDuesAmount(e.currentTarget.value)}
                required
                aria-label="Outstanding Dues Amount"
              />
              <TextInput
                label="Remarks"
                value={signoffRemarks}
                onChange={(e) => setSignoffRemarks(e.currentTarget.value)}
                aria-label="Remarks"
              />
            </>
          ) : (
            <Text size="sm">
              Finalizing will verify that all 6 institutional departments have recorded CLEARED status and will issue an official clearance certificate number.
            </Text>
          )}
        </Stack>
      </FormModal>
    </Container>
  );
}
