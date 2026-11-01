import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useForwardClaimPHC,
  useProcessClaimPayment,
  useReimbursementReviewQueue,
  useSanctionClaim,
  useVerifyClaimAccounts,
} from "../api/hooks";
import type { ReimbursementClaim } from "../api/types";

export default function ReimbursementReviewPage() {
  const { can } = useAuth();
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const { data: queue, isPending, error } = useReimbursementReviewQueue(selectedStage === "all" ? undefined : selectedStage);

  const [activeClaim, setActiveClaim] = useState<ReimbursementClaim | null>(null);
  const [phcModalOpen, setPhcModalOpen] = useState(false);
  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [sanctionModalOpen, setSanctionModalOpen] = useState(false);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);

  // Form states
  const [comments, setComments] = useState("");
  const [amountVerified, setAmountVerified] = useState<number | string>(0);
  const [sanctionDecision, setSanctionDecision] = useState<"approve" | "reject">("approve");
  const [sanctionedAmount, setSanctionedAmount] = useState<number | string>(0);
  const [paymentRef, setPaymentRef] = useState("");

  const forwardPHCMutation = useForwardClaimPHC();
  const verifyAccountsMutation = useVerifyClaimAccounts();
  const sanctionMutation = useSanctionClaim();
  const paymentMutation = useProcessClaimPayment();

  // Role permissions
  const canPHCReview = can("phc.reimbursement.review");
  const canVerify = can("phc.reimbursement.verify");
  const canSanction = can("phc.reimbursement.sanction");
  const canPay = can("phc.reimbursement.pay");

  const handlePHCForward = async () => {
    if (!activeClaim) return;
    try {
      await forwardPHCMutation.mutateAsync({ claimId: activeClaim.id, comments });
      notifications.show({ title: "Forwarded", message: "Claim reviewed and forwarded to Accounts & Audit (AFR-PHC-018).", color: "teal" });
      setPhcModalOpen(false);
      setComments("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to forward claim.", color: "red" });
    }
  };

  const handleAccountsVerify = async () => {
    if (!activeClaim) return;
    try {
      await verifyAccountsMutation.mutateAsync({
        claimId: activeClaim.id,
        amountVerified: Number(amountVerified),
        comments,
      });
      notifications.show({ title: "Verified", message: "Financial verification completed and forwarded for Sanction (AFR-PHC-019).", color: "teal" });
      setVerifyModalOpen(false);
      setComments("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to verify claim.", color: "red" });
    }
  };

  const handleSanction = async () => {
    if (!activeClaim) return;
    try {
      await sanctionMutation.mutateAsync({
        claimId: activeClaim.id,
        decision: sanctionDecision,
        sanctionedAmount: Number(sanctionedAmount),
        comments,
      });
      const outcome = sanctionDecision === "approve" ? "Approved for Payment" : "Rejected (Terminal)";
      notifications.show({ title: "Sanction Recorded", message: `Claim is now ${outcome} (AFR-PHC-020).`, color: sanctionDecision === "approve" ? "teal" : "red" });
      setSanctionModalOpen(false);
      setComments("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to record sanction.", color: "red" });
    }
  };

  const handlePayment = async () => {
    if (!activeClaim) return;
    try {
      await paymentMutation.mutateAsync({
        claimId: activeClaim.id,
        paymentReference: paymentRef,
        comments,
      });
      notifications.show({ title: "Reimbursed", message: `Payment processed. Claim ${activeClaim.claim_number} is closed (AFR-PHC-021).`, color: "green" });
      setPaymentModalOpen(false);
      setPaymentRef("");
      setComments("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to record payment.", color: "red" });
    }
  };

  if (error) return <ErrorState error={error} />;

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Reimbursement Review & Processing Queue"
        subtitle="Ordered multi-actor progression: PHC Review → Accounts Verification → Sanction → Payment (CW-PHC-01)"
      />

      <Tabs value={selectedStage} onChange={(v) => setSelectedStage(v || "all")} mb="md">
        <Tabs.List>
          <Tabs.Tab value="all">All Active Claims</Tabs.Tab>
          <Tabs.Tab value="Pending PHC Review">1. PHC Staff Review</Tabs.Tab>
          <Tabs.Tab value="Pending Accounts Verification">2. Accounts Verification</Tabs.Tab>
          <Tabs.Tab value="Pending Sanction">3. Sanction Approval</Tabs.Tab>
          <Tabs.Tab value="Approved for Payment">4. Payment Processing</Tabs.Tab>
        </Tabs.List>
      </Tabs>

      {isPending ? (
        <Text c="dimmed">Loading queue...</Text>
      ) : !queue || queue.length === 0 ? (
        <Card withBorder p="xl">
          <Text c="dimmed" ta="center">
            No claims currently pending action in this stage.
          </Text>
        </Card>
      ) : (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Claim #</Table.Th>
              <Table.Th>Claimant</Table.Th>
              <Table.Th>Expense Date</Table.Th>
              <Table.Th>Prescription #</Table.Th>
              <Table.Th>Claimed</Table.Th>
              <Table.Th>Approved</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Workflow Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {queue.map((claim) => (
              <Table.Tr key={claim.id}>
                <Table.Td fw={600}>{claim.claim_number}</Table.Td>
                <Table.Td>
                  <Badge variant="light" color="gray">
                    User {claim.claimant_user_id}
                  </Badge>
                </Table.Td>
                <Table.Td>{claim.expense_date}</Table.Td>
                <Table.Td>Rx #{claim.prescription_number}</Table.Td>
                <Table.Td fw={500}>₹{claim.amount_claimed}</Table.Td>
                <Table.Td fw={600} c={claim.amount_approved ? "teal" : "dimmed"}>
                  {claim.amount_approved ? `₹${claim.amount_approved}` : "—"}
                </Table.Td>
                <Table.Td>
                  <Badge
                    color={
                      claim.status === "Pending PHC Review"
                        ? "blue"
                        : claim.status === "Pending Accounts Verification"
                        ? "indigo"
                        : claim.status === "Pending Sanction"
                        ? "orange"
                        : claim.status === "Approved for Payment"
                        ? "teal"
                        : "gray"
                    }
                  >
                    {claim.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {claim.status === "Pending PHC Review" && canPHCReview && (
                    <Button
                      size="xs"
                      color="blue"
                      onClick={() => {
                        setActiveClaim(claim);
                        setPhcModalOpen(true);
                      }}
                    >
                      PHC Review → Forward
                    </Button>
                  )}

                  {claim.status === "Pending Accounts Verification" && canVerify && (
                    <Button
                      size="xs"
                      color="indigo"
                      onClick={() => {
                        setActiveClaim(claim);
                        setAmountVerified(claim.amount_claimed);
                        setVerifyModalOpen(true);
                      }}
                    >
                      Financial Verify
                    </Button>
                  )}

                  {claim.status === "Pending Sanction" && canSanction && (
                    <Button
                      size="xs"
                      color="orange"
                      onClick={() => {
                        setActiveClaim(claim);
                        setSanctionedAmount(claim.amount_approved || claim.amount_claimed);
                        setSanctionModalOpen(true);
                      }}
                    >
                      Decide Sanction
                    </Button>
                  )}

                  {claim.status === "Approved for Payment" && canPay && (
                    <Button
                      size="xs"
                      color="teal"
                      onClick={() => {
                        setActiveClaim(claim);
                        setPaymentRef(`TXN-${Date.now().toString().slice(-6)}`);
                        setPaymentModalOpen(true);
                      }}
                    >
                      Process Payment
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* Stage 1: PHC Review Modal */}
      <Modal opened={phcModalOpen} onClose={() => setPhcModalOpen(false)} title={`PHC Review: ${activeClaim?.claim_number}`}>
        <Stack>
          <Text size="sm">
            Claimant: User {activeClaim?.claimant_user_id} | Amount Claimed: ₹{activeClaim?.amount_claimed}
          </Text>
          <Text size="xs" c="dimmed">
            PHC Staff validates clinical legitimacy of prescription and treatment (CW-PHC-01 Step 2).
          </Text>
          <Textarea label="Review Remarks" placeholder="Prescription and treatment verified." value={comments} onChange={(e) => setComments(e.currentTarget.value)} />
          <Button fullWidth color="blue" onClick={handlePHCForward} loading={forwardPHCMutation.isPending}>
            Confirm PHC Review & Forward to Accounts
          </Button>
        </Stack>
      </Modal>

      {/* Stage 2: Accounts Verification Modal */}
      <Modal opened={verifyModalOpen} onClose={() => setVerifyModalOpen(false)} title={`Accounts & Audit Verification: ${activeClaim?.claim_number}`}>
        <Stack>
          <Text size="sm">Claim Amount: ₹{activeClaim?.amount_claimed}</Text>
          <NumberInput
            label="Verified Amount (₹)"
            description="Accounts & Audit verifies itemized medical bills and vouchers"
            value={amountVerified}
            onChange={setAmountVerified}
            min={1}
            required
          />
          <Textarea label="Accounts Remarks" placeholder="Vouchers audited against institute norms." value={comments} onChange={(e) => setComments(e.currentTarget.value)} />
          <Button fullWidth color="indigo" onClick={handleAccountsVerify} loading={verifyAccountsMutation.isPending}>
            Complete Financial Verification & Forward for Sanction
          </Button>
        </Stack>
      </Modal>

      {/* Stage 3: Sanction Approval Modal */}
      <Modal opened={sanctionModalOpen} onClose={() => setSanctionModalOpen(false)} title={`Approving Authority Sanction: ${activeClaim?.claim_number}`}>
        <Stack>
          <Select
            label="Sanction Decision"
            data={[
              { value: "approve", label: "Approve Sanction" },
              { value: "reject", label: "Reject Claim (Terminal)" },
            ]}
            value={sanctionDecision}
            onChange={(v) => setSanctionDecision((v as any) || "approve")}
            required
          />
          {sanctionDecision === "approve" && (
            <NumberInput
              label="Sanctioned Amount (₹)"
              value={sanctionedAmount}
              onChange={setSanctionedAmount}
              min={1}
              required
            />
          )}
          <Textarea
            label={sanctionDecision === "approve" ? "Approval Remarks" : "Rejection Reason (Mandatory)"}
            placeholder={sanctionDecision === "approve" ? "Sanctioned as recommended." : "State specific reason for rejection."}
            value={comments}
            onChange={(e) => setComments(e.currentTarget.value)}
            required={sanctionDecision === "reject"}
          />
          <Button
            fullWidth
            color={sanctionDecision === "approve" ? "teal" : "red"}
            onClick={handleSanction}
            loading={sanctionMutation.isPending}
          >
            {sanctionDecision === "approve" ? "Approve for Payment" : "Reject Claim"}
          </Button>
        </Stack>
      </Modal>

      {/* Stage 4: Process Payment Modal */}
      <Modal opened={paymentModalOpen} onClose={() => setPaymentModalOpen(false)} title={`Process Payment: ${activeClaim?.claim_number}`}>
        <Stack>
          <Text size="sm">Sanctioned Amount: ₹{activeClaim?.amount_approved || activeClaim?.amount_claimed}</Text>
          <TextInput
            label="Bank / Voucher Payment Reference"
            placeholder="e.g. UTR / Cheque / Voucher Number"
            value={paymentRef}
            onChange={(e) => setPaymentRef(e.currentTarget.value)}
            required
          />
          <Textarea label="Payment Notes" placeholder="Disbursed to claimant account." value={comments} onChange={(e) => setComments(e.currentTarget.value)} />
          <Button fullWidth color="green" onClick={handlePayment} loading={paymentMutation.isPending}>
            Complete Payment & Close Claim as Reimbursed
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
