import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  MultiSelect,
  NumberInput,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExternalLinkAlt, FaPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAttachPriorArt,
  usePriorArtSearches,
  useRecordPriorArtSearch,
} from "../api/hooks";
import type { PriorArtSearchRecord } from "../api/types";

export default function PriorArtPage() {
  const [modalOpened, setModalOpened] = useState(false);
  const [attachModalOpened, setAttachModalOpened] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);

  // New Search Form
  const [queryString, setQueryString] = useState("");
  const [databases, setDatabases] = useState<string[]>([
    "Google Patents",
    "Espacenet",
  ]);
  const [resultsCount, setResultsCount] = useState<number | string>(12);
  const [notes, setNotes] = useState("");
  const [applicationId, setApplicationId] = useState<number | string>("");

  // Attach Form
  const [targetAppId, setTargetAppId] = useState<number | string>("");
  const [relevanceNotes, setRelevanceNotes] = useState("");

  const { data, isPending, error } = usePriorArtSearches();
  const searchMutation = useRecordPriorArtSearch();
  const attachMutation = useAttachPriorArt(selectedRecordId ?? 0);

  const handleCreateSearch = async () => {
    if (!queryString.trim()) return;

    try {
      await searchMutation.mutateAsync({
        query_string: queryString.trim(),
        databases_searched: databases,
        results_count: Number(resultsCount) || 0,
        session_notes: notes.trim(),
        application_id: applicationId ? Number(applicationId) : undefined,
      });
      notifications.show({ color: "green", message: "Prior art search session logged." });
      setModalOpened(false);
      setQueryString("");
      setNotes("");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleAttach = async () => {
    if (!selectedRecordId || !targetAppId) return;

    try {
      await attachMutation.mutateAsync({
        application_id: Number(targetAppId),
        relevance_notes: relevanceNotes.trim(),
      });
      notifications.show({ color: "green", message: "Search attached to application." });
      setAttachModalOpened(false);
      setTargetAppId("");
      setRelevanceNotes("");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<PriorArtSearchRecord>[] = [
    {
      key: "query_string",
      header: "Search Query / Strategy",
      render: (row) => (
        <Stack gap={2}>
          <Text fw={600} size="sm">
            {row.query_string}
          </Text>
          <Text size="xs" c="dimmed">
            {row.session_notes || "No notes"}
          </Text>
        </Stack>
      ),
    },
    {
      key: "databases_searched",
      header: "Databases Queried",
      render: (row) => (
        <Group gap="xs">
          {row.databases_searched?.map((db) => (
            <Badge key={db} size="xs" variant="outline">
              {db}
            </Badge>
          ))}
        </Group>
      ),
    },
    {
      key: "results_count",
      header: "Hits Found",
      render: (row) => (
        <Badge color="blue" size="sm">
          {row.results_count} results
        </Badge>
      ),
    },
    {
      key: "application_id",
      header: "Linked Patent",
      render: (row) =>
        row.application_id ? (
          <Text size="xs" fw={500}>
            App #{row.application_id}
          </Text>
        ) : (
          <Text size="xs" c="dimmed">
            Unlinked
          </Text>
        ),
    },
    {
      key: "created_at",
      header: "Conducted At",
      render: (row) => (
        <Text size="xs">{new Date(row.created_at).toLocaleDateString()}</Text>
      ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Button
          size="xs"
          variant="light"
          leftSection={<FaExternalLinkAlt />}
          onClick={() => {
            setSelectedRecordId(row.id);
            setAttachModalOpened(true);
          }}
        >
          Attach
        </Button>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Prior Art Search Registry"
        subtitle="Global patentability searches, non-patent literature exploration, and prior art mapping."
        action={
          <Button
            leftSection={<FaPlus />}
            color="blue"
            onClick={() => setModalOpened(true)}
          >
            Log Search Session
          </Button>
        }
      />

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No prior art searches recorded",
            description: "Log your first patentability search or exploration session.",
          }}
        />
      </Card>

      {/* New Search Modal */}
      <FormModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title="Log Prior Art Search"
        onSubmit={handleCreateSearch}
        submitLabel="Save Search Record"
        submitting={searchMutation.isPending}
        disabled={!queryString.trim()}
        disabledReason={!queryString.trim() ? "Query string is required" : undefined}
      >
        <Stack gap="md">
          <TextInput
            label="Boolean Query String / Keywords"
            placeholder="E.g. ((solid-state battery) AND (separator OR electrolyte))"
            value={queryString}
            onChange={(e) => setQueryString(e.target.value)}
            required
          />

          <MultiSelect
            label="Databases & Patent Registries Searched"
            data={[
              "Google Patents",
              "Espacenet",
              "USPTO PatentsView",
              "IPO InPASS",
              "WIPO Patentscope",
              "IEEE Xplore",
              "PubMed",
            ]}
            value={databases}
            onChange={setDatabases}
            required
          />

          <NumberInput
            label="Relevant Prior Art Documents Located"
            value={resultsCount}
            onChange={setResultsCount}
            min={0}
            required
          />

          <TextInput
            label="Link to Application ID (Optional)"
            placeholder="Application ID number"
            value={applicationId}
            onChange={(e) => setApplicationId(e.target.value)}
          />

          <Textarea
            label="Search Strategy Notes & Closest Citations"
            placeholder="Identified D1 patent US9041234 disclosing porous polymer matrix..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            minRows={3}
          />
        </Stack>
      </FormModal>

      {/* Attach Modal */}
      <FormModal
        opened={attachModalOpened}
        onClose={() => setAttachModalOpened(false)}
        title="Attach Prior Art to Patent Application"
        onSubmit={handleAttach}
        submitLabel="Confirm Attachment"
        submitting={attachMutation.isPending}
        disabled={!targetAppId}
        disabledReason={!targetAppId ? "Target application ID is required" : undefined}
      >
        <Stack gap="md">
          <TextInput
            label="Target Application ID"
            placeholder="E.g. 1"
            value={targetAppId}
            onChange={(e) => setTargetAppId(e.target.value)}
            required
          />

          <Textarea
            label="Relevance & Distinguishing Features (BR-PMS-005)"
            placeholder="Explains how current claims patentably distinguish over D1/D2..."
            value={relevanceNotes}
            onChange={(e) => setRelevanceNotes(e.target.value)}
            required
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
