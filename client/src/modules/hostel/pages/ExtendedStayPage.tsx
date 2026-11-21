import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus, FaMoneyBillWave } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useExtendedStayCompliance,
  useExtendedStayDecision,
  useExtendedStays,
  useHostels,
  useSubmitExtendedStay,
} from "../api/hooks";
import type { ExtendedStayRequest } from "../api/types";

export default function ExtendedStayPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>("all");

  const {
    data: stays,
    isPending,
    error,
  } = useExtendedStays({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    status: activeTab !== "all" ? activeTab! : undefined,
  });

  const submitMutation = useSubmitExtendedStay();
  const decisionMutation = useExtendedStayDecision();
  const complianceMutation = useExtendedStayCompliance();

  // Request modal
  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [sHostelId, setSHostelId] = useState<string | null>(null);
  const [sReason, setSReason] = useState<string | null>("internship");
  const [sStart, setSStart] = useState("");
  const [sEnd, setSEnd] = useState("");
  const [sRemarks, setSRemarks] = useState("");

  // Decision modal (Warden)
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [selectedStay, setSelectedStay] = useState<ExtendedStayRequest | null>(null);
  const [decisionType, setDecisionType] = useState<"approved" | "rejected">("approved");
  const [decisionRemarks, setDecisionRemarks] = useState("");

  // Compliance modal (Charges & Payment)
  const [complianceModalOpen, setComplianceModalOpen] = useState(false);
  const [chargeAmount, setChargeAmount] = useState<number | string>(0);
  const [paymentDeadline, setPaymentDeadline] = useState("");
  const [paymentStatus, setPaymentStatus] = useState<string | null>("pending");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleRequest = async () => {
    if (!sHostelId || !sStart || !sEnd) return;
    await submitMutation.mutateAsync({
      hostel: Number(sHostelId),
      stay_reason: sReason || "other",
      start_date: sStart,
      end_date: sEnd,
      remarks: sRemarks,
    });
    setRequestModalOpen(false);
    setSStart("");
    setSEnd("");
    setSRemarks("");
  };

  const handleDecision = async () => {
    if (!selectedStay) return;
    await decisionMutation.mutateAsync({
      id: selectedStay.id,
      decision: decisionType,
      remarks: decisionRemarks,
    });
    setDecisionModalOpen(false);
    setDecisionRemarks("");
  };

  const handleCompliance = async () => {
    if (!selectedStay) return;
    await complianceMutation.mutateAsync({
      id: selectedStay.id,
      data: {
        charge_amount: Number(chargeAmount) || 0,
        payment_deadline: paymentDeadline || null,
        payment_status: paymentStatus || "pending",
      },
    });
    setComplianceModalOpen(false);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "submitted":
        return <Badge color="blue">Submitted</Badge>;
      case "approved":
        return <Badge color="teal">Approved</Badge>;
      case "rejected":
        return <Badge color="red">Rejected</Badge>;
      default:
        return <Badge color="gray">{status}</Badge>;
    }
  };

  const getComplianceBadge = (status: string) => {
    switch (status) {
      case "compliant":
        return <Badge color="green" variant="light">Compliant / Paid</Badge>;
      case "non_compliant":
        return <Badge color="red" variant="filled">Non-Compliant</Badge>;
      case "waived":
        return <Badge color="violet" variant="light">Waived</Badge>;
      default:
        return <Badge color="yellow" variant="outline">Pending Payment</Badge>;
    }
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Vacation Extended Stay"
          subtitle="Manage student requests to remain in hostel during vacation, academic breaks, or internships"
          action={
            <Button
              leftSection={<FaPlus />}
              onClick={() => {
                if (hostels && hostels.length > 0 && hostels[0]) {
                  setSHostelId(String(hostels[0].id));
                }
                setRequestModalOpen(true);
              }}
            >
              Request Extended Stay
            </Button>
          }
        />

        <Card withBorder radius="md">
          <Group justify="space-between" mb="md">
            <Select
              placeholder="Filter by hostel"
              clearable
              value={selectedHostel}
              onChange={setSelectedHostel}
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              style={{ width: 280 }}
            />

            <Tabs value={activeTab} onChange={setActiveTab}>
              <Tabs.List>
                <Tabs.Tab value="all">All Requests</Tabs.Tab>
                <Tabs.Tab value="submitted">Pending Decision</Tabs.Tab>
                <Tabs.Tab value="approved">Approved</Tabs.Tab>
                <Tabs.Tab value="rejected">Rejected</Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>

          <DataTable<ExtendedStayRequest>
            rows={stays || []}
            loading={isPending}
            rowKey={(r) => r.id}
            columns={[
              {
                key: "id",
                header: "ID",
                render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
              },
              {
                key: "hostel",
                header: "Hostel",
                render: (r) => <Text size="sm" fw={500}>{r.hostel_name}</Text>,
              },
              {
                key: "student",
                header: "Student",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm">{r.student_name || "Unknown"}</Text>
                    <Text size="xs" c="dimmed">{r.student_roll_number}</Text>
                  </Stack>
                ),
              },
              {
                key: "reason",
                header: "Reason & Period",
                render: (r) => (
                  <Stack gap={2}>
                    <Badge size="xs" variant="outline">{r.stay_reason}</Badge>
                    <Text size="xs" fw={500}>{r.start_date} to {r.end_date}</Text>
                    {r.remarks && <Text size="xs" c="dimmed">{r.remarks}</Text>}
                  </Stack>
                ),
              },
              {
                key: "status",
                header: "Warden Status",
                render: (r) => getStatusBadge(r.status),
              },
              {
                key: "charges",
                header: "Charges & Compliance",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="xs" fw={600}>₹{Number(r.charge_amount || 0).toLocaleString()}</Text>
                    {getComplianceBadge(r.payment_status)}
                    {r.payment_deadline && (
                      <Text size="xs" c="dimmed">Due: {r.payment_deadline}</Text>
                    )}
                  </Stack>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                render: (r) => (
                  <Group gap="xs">
                    {r.status === "submitted" && (
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() => {
                          setSelectedStay(r);
                          setDecisionType("approved");
                          setDecisionRemarks("");
                          setDecisionModalOpen(true);
                        }}
                      >
                        Warden Review
                      </Button>
                    )}
                    {r.status === "approved" && (
                      <Button
                        size="xs"
                        variant="outline"
                        leftSection={<FaMoneyBillWave />}
                        onClick={() => {
                          setSelectedStay(r);
                          setChargeAmount(Number(r.charge_amount || 0));
                          setPaymentDeadline(r.payment_deadline || "");
                          setPaymentStatus(r.payment_status || "pending");
                          setComplianceModalOpen(true);
                        }}
                      >
                        Update Fee
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
            empty={{
              title: "No Extended Stay Requests",
              description: "No extended stay requests found matching the current filter.",
            }}
          />
        </Card>

        {/* Modal: Request Extended Stay */}
        <Modal
          opened={requestModalOpen}
          onClose={() => setRequestModalOpen(false)}
          title="Submit Vacation Extended Stay Request"
          size="md"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={sHostelId}
              onChange={setSHostelId}
            />

            <Select
              label="Reason for Stay"
              required
              data={[
                { value: "internship", label: "Industrial / Academic Internship" },
                { value: "project", label: "Research / Final Year Project" },
                { value: "academic", label: "Remedial / Summer Semester Courses" },
                { value: "sports", label: "Inter-IIIT / Sports Camp" },
                { value: "other", label: "Other Special Reason" },
              ]}
              value={sReason}
              onChange={setSReason}
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                required
                value={sStart}
                onChange={(e) => setSStart(e.target.value)}
              />
              <TextInput
                label="End Date"
                type="date"
                required
                value={sEnd}
                onChange={(e) => setSEnd(e.target.value)}
              />
            </Group>

            <Textarea
              label="Details / Project Mentor / Organization"
              placeholder="Provide organization details, supervisor contact, or lab location..."
              minRows={2}
              value={sRemarks}
              onChange={(e) => setSRemarks(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRequestModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={submitMutation.isPending}
                disabled={!sHostelId || !sStart || !sEnd}
                onClick={handleRequest}
              >
                Submit Request
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Warden Review */}
        <Modal
          opened={decisionModalOpen}
          onClose={() => setDecisionModalOpen(false)}
          title={`Warden Decision on Extended Stay #${selectedStay?.id}`}
          size="md"
        >
          <Stack gap="sm">
            <Card withBorder p="xs">
              <Text size="sm" fw={600}>
                {selectedStay?.student_name} ({selectedStay?.student_roll_number})
              </Text>
              <Text size="xs" c="dimmed">
                {selectedStay?.stay_reason?.toUpperCase()} • {selectedStay?.start_date} to {selectedStay?.end_date}
              </Text>
            </Card>

            <Select
              label="Decision"
              required
              data={[
                { value: "approved", label: "Approve Extended Stay" },
                { value: "rejected", label: "Reject Request" },
              ]}
              value={decisionType}
              onChange={(v) => setDecisionType(v as "approved" | "rejected")}
            />

            <Textarea
              label="Decision Remarks / Warden Directive"
              placeholder="Approved subject to payment of mess/electricity charges..."
              minRows={2}
              value={decisionRemarks}
              onChange={(e) => setDecisionRemarks(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setDecisionModalOpen(false)}>
                Cancel
              </Button>
              <Button
                color={decisionType === "approved" ? "teal" : "red"}
                loading={decisionMutation.isPending}
                onClick={handleDecision}
              >
                Confirm Decision
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Compliance & Fee Update */}
        <Modal
          opened={complianceModalOpen}
          onClose={() => setComplianceModalOpen(false)}
          title={`Update Fee & Compliance for #${selectedStay?.id}`}
          size="md"
        >
          <Stack gap="sm">
            <NumberInput
              label="Applicable Charge Amount (₹)"
              min={0}
              value={chargeAmount}
              onChange={setChargeAmount}
            />

            <TextInput
              label="Payment Deadline"
              type="date"
              value={paymentDeadline}
              onChange={(e) => setPaymentDeadline(e.target.value)}
            />

            <Select
              label="Payment Compliance Status"
              data={[
                { value: "pending", label: "Pending Payment" },
                { value: "compliant", label: "Compliant / Dues Paid" },
                { value: "non_compliant", label: "Non-Compliant (Overdue)" },
                { value: "waived", label: "Waived / Exempted by Authority" },
              ]}
              value={paymentStatus}
              onChange={setPaymentStatus}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setComplianceModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={complianceMutation.isPending}
                onClick={handleCompliance}
              >
                Save Compliance
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
