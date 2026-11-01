import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Tabs,
  Text,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaCoins, FaPlaneDeparture } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCpdaClaims, useLtcClaims, useVerifyCpda, useVerifyLtc } from "../api/hooks";
import type { CpdaRequest, LtcRequest } from "../api/types";

export default function VerificationQueuePage() {
  const { data: ltcClaims, isPending: ltcLoading, error: ltcError } = useLtcClaims();
  const { data: cpdaClaims, isPending: cpdaLoading, error: cpdaError } = useCpdaClaims();

  const verifyLtc = useVerifyLtc();
  const verifyCpda = useVerifyCpda();

  const [activeTab, setActiveTab] = useState<string | null>("ltc");

  // Modal state
  const [targetId, setTargetId] = useState<number | null>(null);
  const [modalType, setModalType] = useState<"ltc" | "cpda" | null>(null);
  const [verdict, setVerdict] = useState<string>("verified");
  const [remarks, setRemarks] = useState<string>("");

  if (ltcError || cpdaError) {
    return (
      <Container size="xl">
        <ErrorState error={ltcError || cpdaError} />
      </Container>
    );
  }

  const pendingLtc = (ltcClaims ?? []).filter((l) => l.verification_status === "pending_verification");
  const pendingCpda = (cpdaClaims ?? []).filter((c) => c.verification_status === "pending_verification");

  const handleVerify = () => {
    if (!targetId || !modalType) return;

    const callback = {
      onSuccess: () => {
        notifications.show({
          title: "Verification Recorded",
          message: `Claim marked as ${verdict}.`,
          color: "teal",
        });
        setTargetId(null);
        setModalType(null);
        setRemarks("");
      },
      onError: (err: unknown) => {
        notifications.show({
          title: "Verification Failed",
          message: errorMessage(err),
          color: "red",
        });
      },
    };

    if (modalType === "ltc") {
      verifyLtc.mutate({ id: targetId, verdict, remarks }, callback);
    } else {
      verifyCpda.mutate({ id: targetId, verdict, remarks }, callback);
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="HR Claims Verification Queue"
        subtitle="Verify block year eligibility, entitlement ceilings, and supporting vouchers (BR-HR-017, BR-HR-022)"
      />

      <Tabs value={activeTab} onChange={setActiveTab} radius="md">
        <Tabs.List mb="lg">
          <Tabs.Tab
            value="ltc"
            leftSection={<FaPlaneDeparture size={14} />}
            rightSection={<Badge size="xs" color="orange">{pendingLtc.length}</Badge>}
          >
            LTC Eligibility Checks
          </Tabs.Tab>
          <Tabs.Tab
            value="cpda"
            leftSection={<FaCoins size={14} />}
            rightSection={<Badge size="xs" color="grape">{pendingCpda.length}</Badge>}
          >
            CPDA Document Checks
          </Tabs.Tab>
        </Tabs.List>

        {/* LTC Verification */}
        <Tabs.Panel value="ltc">
          <Card withBorder padding="lg" radius="md">
            <DataTable<LtcRequest>
              rows={pendingLtc}
              loading={ltcLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                icon: FaCheckCircle,
                title: "No LTC claims awaiting verification",
                description: "All submitted LTC claims have been verified by HR.",
              }}
              columns={[
                {
                  key: "user_id",
                  header: "Employee",
                  render: (r) => <Text size="sm" fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "block_year",
                  header: "Block Year",
                  render: (r) => <Badge variant="light">{r.block_year}</Badge>,
                },
                {
                  key: "journey",
                  header: "Route",
                  render: (r) => <Text size="sm">{r.travel_from} &rarr; {r.travel_to}</Text>,
                },
                {
                  key: "dates",
                  header: "Travel Dates",
                  render: (r) => <Text size="xs" c="dimmed">{r.travel_start_date} to {r.travel_end_date}</Text>,
                },
                {
                  key: "amount",
                  header: "Claimed Amount",
                  render: (r) => <Text size="sm" fw={700}>₹{Number(r.estimated_amount).toLocaleString("en-IN")}</Text>,
                },
                {
                  key: "actions",
                  header: "Verification",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="orange"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("ltc");
                        setVerdict("verified");
                      }}
                    >
                      Verify Claim
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        {/* CPDA Verification */}
        <Tabs.Panel value="cpda">
          <Card withBorder padding="lg" radius="md">
            <DataTable<CpdaRequest>
              rows={pendingCpda}
              loading={cpdaLoading}
              rowKey={(r) => r.id}
              minWidth={850}
              empty={{
                icon: FaCheckCircle,
                title: "No CPDA claims awaiting verification",
                description: "All submitted CPDA claims have been verified by HR.",
              }}
              columns={[
                {
                  key: "user_id",
                  header: "Faculty User",
                  render: (r) => <Text size="sm" fw={600}>User #{r.user_id}</Text>,
                },
                {
                  key: "purpose",
                  header: "Expenditure Purpose",
                  render: (r) => <Text size="sm" lineClamp={1}>{r.purpose}</Text>,
                },
                {
                  key: "amount",
                  header: "Amount",
                  render: (r) => <Text size="sm" fw={700}>₹{Number(r.amount).toLocaleString("en-IN")}</Text>,
                },
                {
                  key: "date",
                  header: "Submitted",
                  render: (r) => <Text size="xs" c="dimmed">{new Date(r.created_at).toLocaleDateString()}</Text>,
                },
                {
                  key: "actions",
                  header: "Verification",
                  render: (r) => (
                    <Button
                      size="xs"
                      color="grape"
                      onClick={() => {
                        setTargetId(r.id);
                        setModalType("cpda");
                        setVerdict("verified");
                      }}
                    >
                      Verify Vouchers
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Verify Modal */}
      <Modal
        opened={modalType != null}
        onClose={() => setModalType(null)}
        title="HR Eligibility & Documentation Verdict"
        size="md"
      >
        <Stack gap="md">
          <Select
            label="Verification Verdict"
            required
            value={verdict}
            onChange={(v) => v && setVerdict(v)}
            data={[
              { value: "verified", label: "Verified & Eligible (Forward for approval)" },
              { value: "returned", label: "Return for Clarification / Resubmission" },
              { value: "rejected", label: "Reject (Ineligible / Policy violation)" },
            ]}
          />

          <Textarea
            label="Verification Notes & Citations"
            placeholder="e.g. Block entitlement verified under CCS LTC rules..."
            rows={3}
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalType(null)}>
              Cancel
            </Button>
            <Button
              color={verdict === "rejected" ? "red" : verdict === "returned" ? "orange" : "teal"}
              loading={verifyLtc.isPending || verifyCpda.isPending}
              onClick={handleVerify}
            >
              Submit Verdict
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
