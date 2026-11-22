import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Paper,
  Progress,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCoins, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCpdaClaims, useMyServiceRecord, useSubmitCpda } from "../api/hooks";
import type { CpdaRequest } from "../api/types";

export default function CpdaPage() {
  const { data: claims, isPending, error } = useCpdaClaims();
  const { data: serviceRecord } = useMyServiceRecord();
  const submitMutation = useSubmitCpda();
  const { can } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<CpdaRequest | null>(null);

  // Form states
  const [requestType, setRequestType] = useState<string>("reimbursement");
  const [purpose, setPurpose] = useState<string>("");
  const [amount, setAmount] = useState<number>(15000);
  const [receiptUrl, setReceiptUrl] = useState<string>("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const cpdaBalance = Number(serviceRecord?.cpda_balance ?? 300000);
  const totalGrant = 300000;
  const utilized = Math.max(0, totalGrant - cpdaBalance);
  const utilizedPercent = Math.min(100, Math.round((utilized / totalGrant) * 100));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!purpose || amount <= 0) {
      notifications.show({
        title: "Validation Error",
        message: "Please specify a valid purpose and claim amount.",
        color: "red",
      });
      return;
    }

    if (amount > cpdaBalance) {
      notifications.show({
        title: "Balance Exceeded",
        message: `Claimed amount (₹${amount}) exceeds available CPDA balance (₹${cpdaBalance}).`,
        color: "red",
      });
      return;
    }

    submitMutation.mutate(
      {
        request_type: requestType,
        purpose,
        amount,
        supporting_documents: receiptUrl ? [receiptUrl] : [],
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "CPDA Claim Submitted",
            message: "Your CPDA claim has been submitted for verification.",
            color: "teal",
          });
          setModalOpen(false);
          setPurpose("");
          setReceiptUrl("");
        },
        onError: (err) => {
          notifications.show({
            title: "Submission Error",
            message: errorMessage(err),
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="CPDA Allowance Management"
        subtitle="Cumulative Professional Development Allowance for conference registrations, books, and memberships (BR-HR-021, BR-HR-022)"
        action={
          can("hr_eis.cpda.apply") && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setModalOpen(true)}
              color="grape"
            >
              Claim CPDA
            </Button>
          )
        }
      />

      {/* CPDA Block Balance Card */}
      <Paper withBorder p="lg" radius="md" mb="lg">
        <Group justify="space-between" mb="xs">
          <div>
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Available CPDA Balance (3-Year Block)
            </Text>
            <Title order={2} c="grape">
              ₹{cpdaBalance.toLocaleString("en-IN")}
            </Title>
          </div>
          <div style={{ textAlign: "right" }}>
            <Text size="xs" c="dimmed">
              Utilized: ₹{utilized.toLocaleString("en-IN")} / ₹{totalGrant.toLocaleString("en-IN")}
            </Text>
            <Badge color="grape" variant="light" mt={4}>
              {utilizedPercent}% utilized
            </Badge>
          </div>
        </Group>
        <Progress value={utilizedPercent} color="grape" size="md" radius="xl" />
      </Paper>

      <Card padding="lg" withBorder radius="md">
        <DataTable<CpdaRequest>
          rows={claims ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            icon: FaCoins,
            title: "No CPDA claims found",
            description: "You have not submitted any CPDA claims yet.",
          }}
          columns={[
            {
              key: "purpose",
              header: "Purpose / Description",
              render: (r) => (
                <div>
                  <Text size="sm" fw={600} lineClamp={1}>
                    {r.purpose}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.request_type.toUpperCase()}
                  </Text>
                </div>
              ),
            },
            {
              key: "amount",
              header: "Claimed Amount",
              render: (r) => (
                <Text size="sm" fw={700}>
                  ₹{Number(r.amount).toLocaleString("en-IN")}
                </Text>
              ),
            },
            {
              key: "verification_status",
              header: "HR Verification",
              render: (r) => <StatusBadge status={r.verification_status} />,
            },
            {
              key: "status",
              header: "Approval Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "disbursement_status",
              header: "Disbursement",
              render: (r) => (
                <Badge
                  color={r.disbursement_status === "paid" ? "teal" : "gray"}
                  variant="outline"
                  size="sm"
                >
                  {r.disbursement_status.toUpperCase()}
                </Badge>
              ),
            },
            {
              key: "created_at",
              header: "Date",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {new Date(r.created_at).toLocaleDateString()}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Details",
              render: (r) => (
                <Button size="xs" variant="subtle" onClick={() => setDetailTarget(r)}>
                  View
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* Claim CPDA Modal */}
      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Submit CPDA Claim" size="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Claim Type"
              required
              value={requestType}
              onChange={(v) => v && setRequestType(v)}
              data={[
                { value: "reimbursement", label: "Reimbursement (Post Expense)" },
                { value: "advance", label: "Advance (Conference / Travel Advance)" },
              ]}
            />

            <Textarea
              label="Expenditure Purpose"
              required
              placeholder="e.g. Registration fee for IEEE International Conference, purchase of research books..."
              rows={3}
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
            />

            <NumberInput
              label="Amount to Claim (₹)"
              required
              min={100}
              max={cpdaBalance}
              step={500}
              value={amount}
              onChange={(v) => setAmount(Number(v) || 0)}
            />

            <TextInput
              label="Receipts / Proof Document Link (Cloud / Drive URL)"
              placeholder="https://..."
              value={receiptUrl}
              onChange={(e) => setReceiptUrl(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={submitMutation.isPending} color="grape">
                Submit Claim
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Claim Details Modal */}
      <Modal
        opened={detailTarget != null}
        onClose={() => setDetailTarget(null)}
        title="CPDA Claim Information"
        size="md"
      >
        {detailTarget && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Purpose:</Text>
              <Text size="sm" fw={600}>{detailTarget.purpose}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Claim Type:</Text>
              <Badge variant="light">{detailTarget.request_type.toUpperCase()}</Badge>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Claimed Amount:</Text>
              <Text size="sm" fw={700}>₹{Number(detailTarget.amount).toLocaleString("en-IN")}</Text>
            </Group>
            {detailTarget.passed_amount && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Disbursed Amount:</Text>
                <Text size="sm" fw={700} c="teal">₹{Number(detailTarget.passed_amount).toLocaleString("en-IN")}</Text>
              </Group>
            )}
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Verification Status:</Text>
              <StatusBadge status={detailTarget.verification_status} />
            </Group>
            {detailTarget.verification_remarks && (
              <Text size="xs" c="dimmed">HR Note: "{detailTarget.verification_remarks}"</Text>
            )}
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Disbursement Status:</Text>
              <Badge color={detailTarget.disbursement_status === "paid" ? "teal" : "gray"}>
                {detailTarget.disbursement_status.toUpperCase()}
              </Badge>
            </Group>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
