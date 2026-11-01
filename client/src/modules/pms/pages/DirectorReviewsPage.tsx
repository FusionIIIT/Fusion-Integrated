import { useState } from "react";
import {
  ActionIcon,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
} from "@mantine/core";
import { FaCheckSquare, FaHistory } from "react-icons/fa";

import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReviewQueue } from "../api/hooks";
import type { PatentApplicationListItem } from "../api/types";
import { DirectorReviewModal } from "../components/DirectorReviewModal";
import { HistoryDrawer } from "../components/HistoryDrawer";
import { StatusBadge } from "../components/StatusBadge";

export default function DirectorReviewsPage() {
  const [reviewAppId, setReviewAppId] = useState<number | null>(null);
  const [historyAppId, setHistoryAppId] = useState<number | null>(null);

  const { data, isPending, error } = useReviewQueue();

  const columns: Column<PatentApplicationListItem>[] = [
    {
      key: "application_no",
      header: "Application No.",
      render: (row) => (
        <Text fw={600} size="sm">
          {row.application_no}
        </Text>
      ),
    },
    {
      key: "title",
      header: "Invention Title",
      render: (row) => (
        <Stack gap={2}>
          <Text fw={500} size="sm">
            {row.title}
          </Text>
          <Text size="xs" c="dimmed">
            Domain: {row.domain} | Lead: {row.primary_inventor_name || "N/A"}
          </Text>
        </Stack>
      ),
    },
    {
      key: "status",
      header: "Review Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "submitted_at",
      header: "Submitted",
      render: (row) => (
        <Text size="xs">
          {row.submitted_at ? new Date(row.submitted_at).toLocaleDateString() : "-"}
        </Text>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Group justify="flex-end" gap="xs">
          <Button
            size="xs"
            color="teal"
            leftSection={<FaCheckSquare />}
            onClick={() => setReviewAppId(row.id)}
          >
            Review & Decide
          </Button>
          <ActionIcon
            variant="subtle"
            color="gray"
            title="Audit History"
            onClick={() => setHistoryAppId(row.id)}
          >
            <FaHistory />
          </ActionIcon>
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Director Review Queue"
        subtitle="Statutory pre-filing evaluation, patentability assessment, and institutional approval (BR-PMS-011..013)."
      />

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No reviews pending",
            description: "No patent disclosures currently awaiting Director review.",
          }}
        />
      </Card>

      <DirectorReviewModal
        applicationId={reviewAppId}
        opened={reviewAppId != null}
        onClose={() => setReviewAppId(null)}
      />

      <HistoryDrawer
        applicationId={historyAppId}
        onClose={() => setHistoryAppId(null)}
      />
    </Container>
  );
}
