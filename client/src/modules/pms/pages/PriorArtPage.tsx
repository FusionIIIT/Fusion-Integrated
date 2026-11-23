import { Badge, Button, Container, Group, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";
import { FaSearch } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, useAttachReference, useSearchPriorArt } from "../api/hooks";
import type { PriorArtReference } from "../api/types";
import { ActionBar, action, num, str } from "../components/ActionBar";

// UC-PMS-004: search recorded prior art, see which outside sources were not searched, attach.
export default function PriorArtPage() {
  const [query, setQuery] = useState("");
  const [codes, setCodes] = useState("");
  const search = useSearchPriorArt();
  const attach = useAttachReference();
  const mine = useApplications();
  const choices = (mine.data?.results ?? []).map((a) => ({ value: String(a.id),
    label: `${a.reference || "Draft"} — ${a.title}` }));
  const run = () => search.mutate({ query, classification_codes:
    codes.split(",").map((c) => c.trim()).filter(Boolean) });
  return (
    <Container size="xl" pt="md">
      <PageHeader title="Prior Art Search" subtitle="Every search is logged for the audit trail"
        action={<ActionBar actions={[action({ key: "attach", label: "Attach a reference",
          title: "Attach prior art to an application", fields: [
            { name: "application_id", label: "Application", type: "select", required: true,
              options: choices },
            { name: "kind", label: "Kind", type: "select", required: true,
              options: [{ value: "patent", label: "Patent" },
                { value: "publication", label: "Publication" }] },
            { name: "title", label: "Title", type: "text", required: true },
            { name: "identifier", label: "Patent number or DOI", type: "text" },
            { name: "url", label: "Link", type: "text" },
            { name: "source_name", label: "Where you found it", type: "text" },
            { name: "notes", label: "Notes", type: "textarea" },
          ], submitLabel: "Attach" }, attach, (v) => ({ id: num(v.application_id),
          kind: str(v.kind), title: str(v.title), identifier: str(v.identifier), url: str(v.url),
          source_name: str(v.source_name), notes: str(v.notes),
          search_id: search.data?.search_id ?? null }))]} />} />
      <Stack gap="md">
        <Group align="flex-end">
          <TextInput label="Search terms" value={query} w={360}
            onChange={(e) => setQuery(e.currentTarget.value)} />
          <TextInput label="IPC classes (comma separated)" value={codes} w={240}
            onChange={(e) => setCodes(e.currentTarget.value)} />
          <Button leftSection={<FaSearch />} onClick={run} loading={search.isPending}
            disabled={!query.trim()}>Search</Button>
        </Group>
        {search.error != null && <ErrorState error={search.error} />}
        {search.data && (
          <>
            <Group gap="xs">
              {search.data.sources.map((s) => (
                <Badge key={s.code} color="gray" variant="light">{s.label}: {s.status}</Badge>
              ))}
            </Group>
            {search.data.suggested_keywords.length > 0 && (
              <Text size="sm">Try also: {search.data.suggested_keywords.join(", ")}</Text>
            )}
            <DataTable<{ reference: PriorArtReference; score: number }>
              rows={search.data.results} rowKey={(r) => r.reference.id}
              empty={{ icon: FaSearch, title: "No recorded references match",
                description: "Outside patent and publication databases are not connected." }}
              columns={[
                { key: "score", header: "Relevance", render: (r) => String(r.score) },
                { key: "title", header: "Title", render: (r) => r.reference.title },
                { key: "identifier", header: "Identifier", render: (r) => r.reference.identifier },
                { key: "kind", header: "Kind", render: (r) => r.reference.kind },
              ]}
            />
          </>
        )}
      </Stack>
    </Container>
  );
}
