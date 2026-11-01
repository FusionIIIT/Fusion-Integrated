import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Container,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { FaExclamationTriangle, FaPaperPlane } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyPrescriptions, useSubmitReimbursement } from "../api/hooks";

export default function ReimbursementApplyPage() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const isStudent = session?.user?.kind?.toLowerCase() === "student";

  const { data: prescriptions, isPending: presPending } = useMyPrescriptions();
  const submitClaimMutation = useSubmitReimbursement();

  const [prescriptionId, setPrescriptionId] = useState<string | null>(null);
  const [expenseDate, setExpenseDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [amountClaimed, setAmountClaimed] = useState<number | string>(1500);
  const [billsDocUrl, setBillsDocUrl] = useState("");
  const [remarks, setRemarks] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isStudent) {
      notifications.show({
        title: "Ineligible Claimant",
        message: "PHC-BR-04: Only institute employees may submit medical bill reimbursement claims.",
        color: "red",
      });
      return;
    }

    if (!prescriptionId || !expenseDate || !amountClaimed) {
      notifications.show({
        title: "Incomplete Claim Form",
        message: "Prescription, expense date, and claim amount are required.",
        color: "orange",
      });
      return;
    }

    try {
      const claim = await submitClaimMutation.mutateAsync({
        prescription_id: Number(prescriptionId),
        expense_date: expenseDate,
        amount_claimed: Number(amountClaimed),
        bills_document_url: billsDocUrl,
        remarks,
      });

      notifications.show({
        title: "Claim Submitted Successfully",
        message: `Claim ${claim.claim_number} is now Pending PHC Review (CW-PHC-01).`,
        color: "teal",
      });
      navigate("/phc/reimbursement/tracking");
    } catch (err: any) {
      const msg = err.response?.data?.error || "Failed to submit claim. Please verify requirements.";
      notifications.show({
        title: "Claim Submission Rejected",
        message: msg,
        color: "red",
      });
    }
  };

  const prescriptionOptions = (prescriptions || []).map((p) => ({
    value: String(p.id),
    label: `Rx #${p.prescription_number} (${p.prescribed_date}) - Dr. ${p.doctor_name}`,
  }));

  return (
    <Container size="md" py="md">
      <PageHeader
        title="Apply for Medical Bill Reimbursement"
        subtitle="Submit expense reimbursement claims for institute employees (AFR-PHC-016; PHC-BR-04, 05, 06)"
      />

      {isStudent && (
        <Alert
          icon={<FaExclamationTriangle size={18} />}
          title="Ineligible: Employee Only Feature (PHC-BR-04)"
          color="red"
          mb="lg"
        >
          Medical bill reimbursement submission is strictly restricted to institute employees (faculty and staff).
          Students are excluded from reimbursement claim submission per institute policy (AFR-PHC-013).
        </Alert>
      )}

      <Card withBorder shadow="sm" radius="md" p="xl">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Associated PHC Prescription"
              description="Each claim must be linked to a valid prescription already recorded for you (PHC-BR-05)"
              placeholder={presPending ? "Loading your recorded prescriptions..." : "Select recorded prescription"}
              data={prescriptionOptions}
              value={prescriptionId}
              onChange={setPrescriptionId}
              required
              disabled={isStudent}
            />

            <TextInput
              label="Medical Expense Date"
              description="Must fall within the configured 90-day submission window (PHC-BR-06)"
              type="date"
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.currentTarget.value)}
              required
              disabled={isStudent}
            />

            <NumberInput
              label="Amount Claimed (₹)"
              placeholder="e.g. 2450.00"
              value={amountClaimed}
              onChange={setAmountClaimed}
              min={1}
              decimalScale={2}
              required
              disabled={isStudent}
            />

            <TextInput
              label="Uploaded Medical Bills / Vouchers URL"
              placeholder="Link to itemized bills scan (e.g. https://... or /bills/clm.pdf)"
              value={billsDocUrl}
              onChange={(e) => setBillsDocUrl(e.currentTarget.value)}
              disabled={isStudent}
            />

            <Textarea
              label="Employee Notes / Justification"
              placeholder="Any additional details regarding the medical emergency or treatment"
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
              rows={3}
              disabled={isStudent}
            />

            <Button
              type="submit"
              size="md"
              leftSection={<FaPaperPlane />}
              color="blue"
              loading={submitClaimMutation.isPending}
              disabled={isStudent}
              mt="md"
            >
              Submit Reimbursement Application
            </Button>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
