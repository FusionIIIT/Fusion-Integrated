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
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaPlus, FaShieldAlt } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateExtendedStay,
  useDecideExtendedStay,
  useExtendedStays,
  useHostels,
  useUpdateExtendedStayCompliance,
} from "../api/hooks";
import type { ExtendedStayReason, ExtendedStayRequest } from "../api/types";

export default function ExtendedStayPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: staysData, error: staysError } = useExtendedStays({ hostel_id: hostelId });

  const createStay = useCreateExtendedStay();
  const decideStay = useDecideExtendedStay();
  const updateCompliance = useUpdateExtendedStayCompliance();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [complianceModalOpen, setComplianceModalOpen] = useState(false);
  const [selectedStay, setSelectedStay] = useState<ExtendedStayRequest | null>(null);

  // Form state
  const [stayHostelId, setStayHostelId] = useState<string | null>(null);
  const [reasonType, setReasonType] = useState<string>("internship");
  const [reasonDetails, setReasonDetails] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [documentUrl, setDocumentUrl] = useState("");

  // Decision state
  const [decision, setDecision] = useState<string>("approved");
  const [charges, setCharges] = useState<number | string>(1500);
  const [paymentDeadline, setPaymentDeadline] = useState("");
  const [decisionRemarks, setDecisionRemarks] = useState("");

  // Compliance state
  const [complianceStatus, setComplianceStatus] = useState<string>("verified");
  const [complianceRemarks, setComplianceRemarks] = useState("");

  const handleCreate = async () => {
    if (!stayHostelId) return;
    try {
      await createStay.mutateAsync({
        hostel: Number(stayHostelId),
        reason_type: reasonType as ExtendedStayReason,
        reason_details: reasonDetails,
        from_date: fromDate,
        to_date: toDate,
        supporting_document_url: documentUrl,
      });
      notifications.show({ title: "Success", message: "Extended stay request submitted", color: "green" });
      setCreateModalOpen(false);
      setReasonDetails("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to submit request", color: "red" });
    }
  };

  const handleDecision = async () => {
    if (!selectedStay) return;
    try {
      await decideStay.mutateAsync({
        id: selectedStay.id,
        decision,
        charge_amount: Number(charges),
        payment_deadline: paymentDeadline || undefined,
        remarks: decisionRemarks,
      });
      notifications.show({ title: "Success", message: `Request marked as ${decision}`, color: "green" });
      setDecisionModalOpen(false);
      setSelectedStay(null);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to record decision", color: "red" });
    }
  };

  const handleCompliance = async () => {
    if (!selectedStay) return;
    try {
      await updateCompliance.mutateAsync({
        id: selectedStay.id,
        compliance_status: complianceStatus,
        remarks: complianceRemarks,
      });
      notifications.show({ title: "Success", message: "Compliance status updated", color: "green" });
      setComplianceModalOpen(false);
      setSelectedStay(null);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to update compliance", color: "red" });
    }
  };

  if (staysError) return <Container size="xl"><ErrorState error={staysError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const stays = staysData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Extended Stays"
        subtitle="Vacation and semester break accommodation permissions, internship validations, and fee compliance"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setCreateModalOpen(true)}>
            Apply for Break Stay
          </Button>
        }
      />

      <Group mb="md">
        <Select
          placeholder="Filter by hostel"
          clearable
          data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
          value={selectedHostel}
          onChange={setSelectedHostel}
          style={{ width: 280 }}
        />
      </Group>

      <Card withBorder radius="md">
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Student</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Reason Category</Table.Th>
              <Table.Th>Stay Period</Table.Th>
              <Table.Th>Fee / Deadline</Table.Th>
              <Table.Th>Approval</Table.Th>
              <Table.Th>Compliance</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {stays.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td fw={600}>{s.student_name || `Student #${s.student_user_id}`}</Table.Td>
                <Table.Td>{s.hostel_name || `Hostel #${s.hostel}`}</Table.Td>
                <Table.Td>
                  <Badge variant="outline">{s.reason_type.toUpperCase()}</Badge>
                  <Text size="xs" c="dimmed" lineClamp={1}>{s.reason_details}</Text>
                </Table.Td>
                <Table.Td>{s.from_date} to {s.to_date}</Table.Td>
                <Table.Td>
                  <Text size="sm">Rs. {s.charge_amount}</Text>
                  <Text size="xs" c="dimmed">{s.payment_deadline ? `Due: ${s.payment_deadline}` : "No deadline"}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={s.status === "approved" ? "green" : s.status === "pending" ? "yellow" : "red"}>
                    {s.status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Badge color={s.compliance_status === "verified" ? "teal" : s.compliance_status === "waived" ? "gray" : "orange"}>
                    {s.compliance_status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {s.status === "pending" && (
                      <Button
                        size="xs"
                        variant="subtle"
                        leftSection={<FaCheck size={12} />}
                        onClick={() => {
                          setSelectedStay(s);
                          setDecisionModalOpen(true);
                        }}
                      >
                        Warden Review
                      </Button>
                    )}
                    {s.status === "approved" && (
                      <Button
                        size="xs"
                        variant="subtle"
                        color="teal"
                        leftSection={<FaShieldAlt size={12} />}
                        onClick={() => {
                          setSelectedStay(s);
                          setComplianceStatus(s.compliance_status);
                          setComplianceModalOpen(true);
                        }}
                      >
                        Compliance
                      </Button>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Modal: Apply */}
      <Modal opened={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Apply for Break Extended Stay" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={stayHostelId}
            onChange={setStayHostelId}
          />
          <Select
            label="Reason Classification"
            required
            data={[
              { value: "internship", label: "Summer / Winter Internship" },
              { value: "project", label: "Academic Research / Sponsored Project" },
              { value: "exam", label: "Competitive Exams / Remedial Classes" },
              { value: "medical", label: "Medical Treatments / Ground" },
              { value: "other", label: "Other Official Permissions" },
            ]}
            value={reasonType}
            onChange={(val) => val && setReasonType(val)}
          />
          <Group grow>
            <TextInput label="From Date" type="date" required value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
            <TextInput label="To Date" type="date" required value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </Group>
          <TextInput label="Supporting Document URL / Drive Link" placeholder="e.g. Internship letter link" value={documentUrl} onChange={(e) => setDocumentUrl(e.target.value)} />
          <Textarea label="Reason Details" required value={reasonDetails} onChange={(e) => setReasonDetails(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            <Button loading={createStay.isPending} onClick={handleCreate}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Warden Review Decision */}
      <Modal opened={decisionModalOpen} onClose={() => setDecisionModalOpen(false)} title={`Warden Review: Request #${selectedStay?.id}`} centered>
        <Stack gap="sm">
          <Select
            label="Decision"
            required
            data={[
              { value: "approved", label: "Approve Extended Stay" },
              { value: "rejected", label: "Reject Request" },
            ]}
            value={decision}
            onChange={(val) => val && setDecision(val)}
          />
          {decision === "approved" && (
            <>
              <NumberInput label="Applicable Hostel Charges (Rs.)" min={0} value={charges} onChange={setCharges} />
              <TextInput label="Payment Deadline" type="date" value={paymentDeadline} onChange={(e) => setPaymentDeadline(e.target.value)} />
            </>
          )}
          <Textarea label="Review Remarks" placeholder="Warden authorization notes" value={decisionRemarks} onChange={(e) => setDecisionRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setDecisionModalOpen(false)}>Cancel</Button>
            <Button loading={decideStay.isPending} onClick={handleDecision}>Confirm Decision</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Compliance Update */}
      <Modal opened={complianceModalOpen} onClose={() => setComplianceModalOpen(false)} title="Verify Fee & Vacation Compliance" centered>
        <Stack gap="sm">
          <Select
            label="Compliance Status"
            required
            data={[
              { value: "verified", label: "Verified (Fee & Documents Complete)" },
              { value: "waived", label: "Waived by Competent Authority" },
              { value: "pending", label: "Pending Verification" },
            ]}
            value={complianceStatus}
            onChange={(val) => val && setComplianceStatus(val)}
          />
          <Textarea label="Compliance Remarks" placeholder="Receipt number / proof check notes" value={complianceRemarks} onChange={(e) => setComplianceRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setComplianceModalOpen(false)}>Cancel</Button>
            <Button color="teal" loading={updateCompliance.isPending} onClick={handleCompliance}>Save Compliance</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
