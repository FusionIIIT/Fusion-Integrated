import { useState } from "react";
import { Alert, Button, Card, Container, Group, List, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle, FaSearch } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePriorArtSearch } from "../api/hooks";
import type { PriorArtResult } from "../api/types";

export default function PriorArtPage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<PriorArtResult | null>(null);
  const searchMutation = usePriorArtSearch();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      notifications.show({
        color: "red",
        title: "Query required",
        message: "Please enter a search query for prior art references.",
      });
      return;
    }

    searchMutation.mutate(query.trim(), {
      onSuccess: (data) => {
        setResult(data);
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Prior art search failed",
          message: errorMessage(err),
        });
      },
    });
  };

  return (
    <Container size="md">
      <PageHeader
        title="Prior Art Search"
        subtitle="Search institutional, national, and international prior-art patent databases"
      />

      <Card padding="lg" withBorder mb="lg">
        <form onSubmit={handleSearch}>
          <Stack gap="md">
            <TextInput
              label="Search Query"
              placeholder="e.g., neural network drone collision avoidance"
              required
              value={query}
              onChange={(e) => setQuery(e.currentTarget.value)}
            />
            <Group justify="flex-end">
              <Button
                type="submit"
                leftSection={<FaSearch size={12} />}
                loading={searchMutation.isPending}
                aria-label="Search Prior Art"
              >
                Search Prior Art
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>

      {searchMutation.isPending && <Text c="dimmed">Searching prior art databases…</Text>}

      {!searchMutation.isPending && result && result.results.length === 0 && (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No results found">
          <Text size="sm">No prior art records matched &quot;{result.query}&quot;.</Text>
        </Alert>
      )}

      {result && result.results.length > 0 && (
        <Card padding="lg" withBorder>
          <Text fw={600} mb="sm">
            Results for: &quot;{result.query}&quot;
          </Text>
          <List spacing="xs" size="sm">
            {result.results.map((item, idx) => (
              <List.Item key={idx}>{item}</List.Item>
            ))}
          </List>
        </Card>
      )}
    </Container>
  );
}
