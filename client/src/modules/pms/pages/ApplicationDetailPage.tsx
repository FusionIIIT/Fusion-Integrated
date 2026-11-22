import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useParams } from "react-router-dom";
import { FaCertificate, FaPaperPlane, FaTimes } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useApplication,
  useApplicationTransactions,
  useSubmitApplication,
  useWithdrawApplication,
} from "../api/hooks";

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const appId = parseInt(id || "0", 10);

  const { data: app, isPending } = useApplication(appId);
  const { data: txns } = useApplicationTransactions(appId);
  const submitMutation = useSubmitApplication();
  const withdrawMutation = useWithdrawApplication();

  const [activeTab, setActiveTab] = useState<string | null>("overview");

  if (isPending || !app) {
    return <Container py="xl"><Text>Loading patent application details...</Text></Container>;
  }

  const handleSubmit = () => {
    submitMutation.mutate(appId, {
      onSuccess: () => {
        notifications.show({ title: "Success", message: "Application submitted for institutional scrutiny.", color: "green" });
      },
      onError: (err: any) => {
        notifications.show({ title: "Submission Failed", message: err.response?.data?.error || "Error submitting application", color: "red" });
      },
    });
  };

  const handleWithdraw = () => {
    withdrawMutation.mutate({ id: appId, reason: "Withdrawn by primary inventor" }, {
      onSuccess: () => {
        notifications.show({ title: "Application Withdrawn", message: "Application withdrawn from consideration.", color: "orange" });
      },
      onError: (err: any) => {
        notifications.show({ title: "Withdrawal Failed", message: err.response?.data?.error || "Error withdrawing application", color: "red" });
      },
    });
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title={`${app.application_no}: ${app.title}`}
        subtitle={`Applicant User #${app.applicant_user_id} • Status: ${app.status.toUpperCase()}`}
        icon={<FaCertificate size={28} />}
        actions={
          <Group>
            {app.status === "draft" && (
              <Button
                color="green"
                leftSection={<FaPaperPlane />}
                loading={submitMutation.isPending}
                onClick={handleSubmit}
              >
                Submit for Scrutiny
              </Button>
            )}
            {["draft", "submitted", "under_review", "needs_revision"].includes(app.status) && (
              <Button
                color="red"
                variant="outline"
                leftSection={<FaTimes />}
                loading={withdrawMutation.isPending}
                onClick={handleWithdraw}
              >
                Withdraw
              </Button>
            )}
          </Group>
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} mt="md">
        <Tabs.List>
          <Tabs.Tab value="overview">Invention Disclosure</Tabs.Tab>
          <Tabs.Tab value="inventors">Co-Inventors ({app.inventors?.length || 0})</Tabs.Tab>
          <Tabs.Tab value="prior_art">Prior Art ({app.prior_art_references?.length || 0})</Tabs.Tab>
          <Tabs.Tab value="finance">Financial Ledger ({txns?.length || 0})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="overview" pt="md">
          <Card shadow="xs" padding="lg" radius="md" withBorder>
            <Stack gap="sm">
              <Group justify="space-between">
                <Text fw={600} size="sm">Filing Specification Type:</Text>
                <Badge variant="light" tt="capitalize">{app.filing_type}</Badge>
              </Group>
              <Group justify="space-between">
                <Text fw={600} size="sm">Current Lifecycle Status:</Text>
                <Badge color="blue">{app.status}</Badge>
              </Group>
              {app.official_filing_number && (
                <Group justify="space-between">
                  <Text fw={600} size="sm">Official Patent Office Filing No:</Text>
                  <Text fw={700} c="blue">{app.official_filing_number}</Text>
                </Group>
              )}
              {app.grant_number && (
                <Group justify="space-between">
                  <Text fw={600} size="sm">Official Patent Grant No:</Text>
                  <Text fw={700} c="green">{app.grant_number}</Text>
                </Group>
              )}
              <Title order={5} mt="md">Abstract</Title>
              <Text size="sm">{app.abstract}</Text>
              <Title order={5} mt="md">Claims</Title>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{app.claims}</Text>
              <Title order={5} mt="md">Detailed Description</Title>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{app.detailed_description || "None provided."}</Text>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="inventors" pt="md">
          <Card shadow="xs" padding="lg" radius="md" withBorder>
            <Stack gap="md">
              {app.inventors?.map((inv) => (
                <Card key={inv.id} withBorder padding="sm">
                  <Group justify="space-between">
                    <div>
                      <Text fw={600}>{inv.inventor_name}</Text>
                      <Text size="xs" c="dimmed">{inv.affiliation || "Institute Member"}</Text>
                    </div>
                    <div>
                      <Badge color="blue">{inv.contribution_percentage}% Contribution</Badge>
                      <Badge ml="xs" color={inv.agreement_signed ? "green" : "orange"}>
                        {inv.agreement_signed ? "Agreement Signed" : "Agreement Pending"}
                      </Badge>
                    </div>
                  </Group>
                </Card>
              ))}
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="prior_art" pt="md">
          <Card shadow="xs" padding="lg" radius="md" withBorder>
            <Stack gap="md">
              {app.prior_art_references?.map((pa) => (
                <Card key={pa.id} withBorder padding="sm">
                  <Text fw={600}>{pa.title}</Text>
                  <Text size="xs" c="dimmed">{pa.citation_type.toUpperCase()} • Ref: {pa.publication_number_or_doi}</Text>
                  <Text size="sm" mt="xs">{pa.relevance_summary}</Text>
                </Card>
              ))}
              {(!app.prior_art_references || app.prior_art_references.length === 0) && (
                <Text size="sm" c="dimmed">No prior art citations recorded.</Text>
              )}
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="finance" pt="md">
          <Card shadow="xs" padding="lg" radius="md" withBorder>
            <Stack gap="md">
              {txns?.map((tx) => (
                <Card key={tx.id} withBorder padding="sm">
                  <Group justify="space-between">
                    <div>
                      <Text fw={600}>{tx.transaction_type.toUpperCase()}</Text>
                      <Text size="xs" c="dimmed">Ref #{tx.reference_no} • {tx.effective_date}</Text>
                    </div>
                    <div>
                      <Text fw={700}>{tx.amount} {tx.currency}</Text>
                      <Badge size="xs" color="blue">{tx.payment_status}</Badge>
                    </div>
                  </Group>
                </Card>
              ))}
              {(!txns || txns.length === 0) && (
                <Text size="sm" c="dimmed">No financial transactions recorded in the ledger.</Text>
              )}
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
