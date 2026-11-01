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
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlaneDeparture, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLtcClaims, useSubmitLtc } from "../api/hooks";
import type { LtcRequest } from "../api/types";

export default function LtcPage() {
  const { data: claims, isPending, error } = useLtcClaims();
  const submitMutation = useSubmitLtc();
  const { can } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [detailTarget, setDetailTarget] = useState<LtcRequest | null>(null);

  // Form states
  const [requestType, setRequestType] = useState<string>("advance");
  const [blockYear, setBlockYear] = useState<string>("2026-2029");
  const [travelFrom, setTravelFrom] = useState<string>("Jabalpur");
  const [travelTo, setTravelTo] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [amount, setAmount] = useState<number>(20000);
  const [docUrl, setDocUrl] = useState<string>("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!travelTo || !startDate || !endDate) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all travel details.",
        color: "red",
      });
      return;
    }

    submitMutation.mutate(
      {
        request_type: requestType,
        block_year: blockYear,
        travel_from: travelFrom,
        travel_to: travelTo,
        travel_start_date: startDate,
        travel_end_date: endDate,
        estimated_amount: amount,
        claimed_amount: requestType === "reimbursement" ? amount : undefined,
        supporting_documents: docUrl ? [{ name: "Estimate / Receipts", url: docUrl }] : [],
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "LTC Claim Submitted",
            message: "Your LTC application has been submitted for HR eligibility verification.",
            color: "teal",
          });
          setModalOpen(false);
          setTravelTo("");
          setStartDate("");
          setEndDate("");
          setDocUrl("");
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
        title="Leave Travel Concession (LTC)"
        subtitle="Submit advance and reimbursement claims for home town / all-India travel (BR-HR-016 to BR-HR-020)"
        action={
          can("hr_eis.ltc.apply") && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setModalOpen(true)}
              color="orange"
            >
              Apply for LTC
            </Button>
          )
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LtcRequest>
          rows={claims ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          empty={{
            icon: FaPlaneDeparture,
            title: "No LTC claims found",
            description: "You have not submitted any LTC claims for this block period.",
          }}
          columns={[
            {
              key: "request_type",
              header: "Type",
              render: (r) => (
                <Badge color={r.request_type === "advance" ? "blue" : "grape"} variant="light">
                  {r.request_type.toUpperCase()}
                </Badge>
              ),
            },
            {
              key: "journey",
              header: "Journey",
              render: (r) => (
                <Text size="sm">
                  {r.travel_from} &rarr; {r.travel_to}
                </Text>
              ),
            },
            {
              key: "dates",
              header: "Travel Dates",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {r.travel_start_date} to {r.travel_end_date}
                </Text>
              ),
            },
            {
              key: "amount",
              header: "Amount",
              render: (r) => (
                <Text size="sm" fw={600}>
                  ₹{Number(r.estimated_amount).toLocaleString("en-IN")}
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
              key: "payment_status",
              header: "Payment",
              render: (r) => (
                <Badge
                  color={r.payment_status === "paid" ? "teal" : "gray"}
                  variant="outline"
                  size="sm"
                >
                  {r.payment_status.toUpperCase()}
                </Badge>
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

      {/* Apply LTC Modal */}
      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Apply for LTC Claim" size="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Claim Type"
              required
              value={requestType}
              onChange={(v) => v && setRequestType(v)}
              data={[
                { value: "advance", label: "LTC Advance (Pre-Travel)" },
                { value: "reimbursement", label: "LTC Reimbursement (Post-Travel Settlement)" },
              ]}
            />

            <TextInput
              label="LTC Block Period"
              required
              value={blockYear}
              onChange={(e) => setBlockYear(e.target.value)}
            />

            <Group grow>
              <TextInput
                label="Journey Origin"
                required
                value={travelFrom}
                onChange={(e) => setTravelFrom(e.target.value)}
              />
              <TextInput
                label="Destination"
                required
                placeholder="e.g. New Delhi, Port Blair"
                value={travelTo}
                onChange={(e) => setTravelTo(e.target.value)}
              />
            </Group>

            <Group grow>
              <TextInput
                label="Departure Date"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <TextInput
                label="Return Date"
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </Group>

            <NumberInput
              label="Estimated / Claimed Amount (₹)"
              required
              min={1000}
              step={1000}
              value={amount}
              onChange={(v) => setAmount(Number(v) || 0)}
            />

            <TextInput
              label="Receipts / Fare Estimates Link (Drive / Cloud URL)"
              placeholder="https://..."
              value={docUrl}
              onChange={(e) => setDocUrl(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={submitMutation.isPending} color="orange">
                Submit LTC Claim
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Details Modal */}
      <Modal
        opened={detailTarget != null}
        onClose={() => setDetailTarget(null)}
        title="LTC Claim Details"
        size="md"
      >
        {detailTarget && (
          <Stack gap="sm">
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Block Year:</Text>
              <Text size="sm" fw={600}>{detailTarget.block_year}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Journey Route:</Text>
              <Text size="sm" fw={600}>{detailTarget.travel_from} &rarr; {detailTarget.travel_to}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Dates:</Text>
              <Text size="sm">{detailTarget.travel_start_date} to {detailTarget.travel_end_date}</Text>
            </Group>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Estimated Amount:</Text>
              <Text size="sm" fw={600}>₹{Number(detailTarget.estimated_amount).toLocaleString("en-IN")}</Text>
            </Group>
            {detailTarget.passed_amount && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Settled Amount:</Text>
                <Text size="sm" fw={700} c="teal">₹{Number(detailTarget.passed_amount).toLocaleString("en-IN")}</Text>
              </Group>
            )}
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Verification Status:</Text>
              <StatusBadge status={detailTarget.verification_status} />
            </Group>
            {detailTarget.verification_remarks && (
              <Text size="xs" c="dimmed">Verification Note: "{detailTarget.verification_remarks}"</Text>
            )}
            <Group justify="space-between">
              <Text size="sm" c="dimmed">Payment Status:</Text>
              <Badge color={detailTarget.payment_status === "paid" ? "teal" : "gray"}>
                {detailTarget.payment_status.toUpperCase()}
              </Badge>
            </Group>
            {detailTarget.payment_reference && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Payment Reference:</Text>
                <Text size="sm" fw={600}>{detailTarget.payment_reference}</Text>
              </Group>
            )}
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
