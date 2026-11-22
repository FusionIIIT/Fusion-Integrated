import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCoins, FaHandHoldingUsd, FaPlaneDeparture } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCpdaClaims, useLtcClaims, useSettleCpda, useSettleLtc } from "../api/hooks";
import type { CpdaRequest, LtcRequest } from "../api/types";

export default function SettlementQueuePage() {
  const { data: ltcClaims, isPending: ltcLoading, error: ltcError } = useLtcClaims();
  const { data: cpdaClaims, isPending: cpdaLoading, error: cpdaError } = useCpdaClaims();

  const settleLtc = useSettleLtc();
  const settleCpda = useSettleCpda();

  const [activeTab, setActiveTab] = useState<string | null>("ltc");

  // Settlement Modal state
  const [targetId, setTargetId] = useState<number | null>(null);
  const [modalType, setModalType] = useState<"ltc" | "cpda" | null>(null);
  const [passedAmount, setPassedAmount] = useState<number>(0);
  const [referenceId, setReferenceId] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");

  if (ltcError || cpdaError) {
    return (
      <Container size="xl">
        <ErrorState error={ltcError || cpdaError} />
      </Container>
    );
  }

  // Filter approved claims awaiting settlement
  const unsettledLtc = (ltcClaims ?? []).filter((l) => l.status === "approved" && l.payment_status !== "paid");
  const unsettledCpda = (cpdaClaims ?? []).filter((c) => c.status === "approved" && c.disbursement_status !== "paid");

  const handleSettle = () => {
    if (!targetId || !modalType || passedAmount <= 0 || !referenceId) {
      notifications.show({
        title: "Validation Error",
        message: "Please specify passed amount and payment reference / voucher number.",
        color: "red",
      });
      return;
    }

    const callback = {
      onSuccess: () => {
        notifications.show({
          title: "Settlement Recorded",
          message: "Payment successfully recorded and financial ledgers updated.",
          color: "teal",
        });
        setTargetId(null);
        setModalType(null);
        setPassedAmount(0);
        setReferenceId("");
        setRemarks("");
      },
      onError: (err: unknown) => {
        notifications.show({
          title: "Settlement Failed",
          message: errorMessage(err),
          color: "red",
        });
      },
    };

    if (modalType === "ltc") {
      settleLtc.mutate({ id: targetId, passed_amount: passedAmount, reference_id: referenceId, remarks }, callback);
    } else {
      settleCpda.mutate({ id: targetId, passed_amount: passedAmount, voucher_no: referenceId, remarks }, callback);
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Finance & Settlement Disbursement Queue"
        subtitle="Record bank transfers, payment voucher references, and ledger adjustments (BR-HR-020, BR-HR-035)"
      />

      <Tabs value={activeTab} onChange={setActiveTab} radius="md">
        <Tabs.List mb="lg">
          <Tabs.Tab
            value="ltc"
            leftSection={<FaPlaneDeparture size={14} />}
            rightSection={<Badge size="xs" color="orange">{unsettledLtc.length}</Badge>}
          >
            Approved LTC Settlement
          </Tabs.Tab>
          <Tabs.Tab
            value="cpda"
            leftSection={<FaCoins size={14} />}
            rightSection={<Badge size="xs" color="grape">{unsettledCpda.length}</Badge>}
          >
            Approved CPDA Disbursement
          </Tabs.Tab>
        </Tabs.List>

        {/* LTC Settlement */}
        <Tabs.Panel value="ltc">
          <Card withBorder padding="lg" radius="md">
            <DataTable<LtcRequest>
              rows={unsettledLtc}
              loading={ltcLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                icon: FaHandHoldingUsd,
                title: "No pending LTC settlements",
                description: "All approved LTC claims have been disbursed and settled.",
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
                  header: "Approved Ceiling",
                  render: (r) => <Text size="sm" fw={700}>₹{Number(r.estimated_amount).toLocaleString("en-IN")}</Text>,
                },
                {
                  key: "actions",
                  header: "Disbursement",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="teal"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("ltc");
                        setPassedAmount(Number(r.estimated_amount));
                        setReferenceId("");
                      }}
                    >
                      Record Settlement
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        {/* CPDA Disbursement */}
        <Tabs.Panel value="cpda">
          <Card withBorder padding="lg" radius="md">
            <DataTable<CpdaRequest>
              rows={unsettledCpda}
              loading={cpdaLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                icon: FaHandHoldingUsd,
                title: "No pending CPDA disbursements",
                description: "All approved CPDA claims have been disbursed.",
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
                  header: "Claimed Amount",
                  render: (r) => <Text size="sm" fw={700}>₹{Number(r.amount).toLocaleString("en-IN")}</Text>,
                },
                {
                  key: "actions",
                  header: "Disbursement",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="teal"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("cpda");
                        setPassedAmount(Number(r.amount));
                        setReferenceId("");
                      }}
                    >
                      Record Disbursement
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Settlement Action Modal */}
      <Modal
        opened={modalType != null}
        onClose={() => setModalType(null)}
        title="Record Financial Disbursement"
        size="md"
      >
        <Stack gap="md">
          <NumberInput
            label="Disbursed / Passed Amount (₹)"
            required
            min={1}
            step={500}
            value={passedAmount}
            onChange={(v) => setPassedAmount(Number(v) || 0)}
          />

          <TextInput
            label="Payment Voucher / Bank UTR Reference"
            required
            placeholder="e.g. UTR-2026-990114"
            value={referenceId}
            onChange={(e) => setReferenceId(e.target.value)}
          />

          <Textarea
            label="Settlement Remarks"
            placeholder="e.g. Credited via direct SBI bank transfer..."
            rows={2}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalType(null)}>
              Cancel
            </Button>
            <Button
              color="teal"
              loading={settleLtc.isPending || settleCpda.isPending}
              onClick={handleSettle}
            >
              Confirm Disbursement
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
