import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Badge, Card, Center, Container, Group, Loader, Select, Stack, Table,
  Text, TextInput,
} from "@mantine/core";
import { FaSearch, FaUsers } from "react-icons/fa";

import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";

interface DirectoryUser {
  user_id: number;
  username: string;
  display_name: string;
  kind: string;
  email: string;
  department: string;
  programme: string;
  discipline: string;
  batch_year: number | null;
}

interface DirectoryResponse {
  results: DirectoryUser[];
}

export default function DirectoryPage() {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<string | null>(null);
  const trimmedQuery = query.trim();
  const enabled = trimmedQuery.length >= 2;

  const { data, isPending, isFetching, error } = useQuery({
    queryKey: ["directory", trimmedQuery, kind],
    queryFn: async () => (await http.get<DirectoryResponse>("/directory/users", {
      params: { q: trimmedQuery, kind: kind || undefined, limit: 100 },
    })).data,
    enabled,
    staleTime: 30_000,
  });

  return (
    <Container size="xl">
      <PageHeader
        title="People Directory"
        subtitle="Search students, faculty and staff from the institute directory"
      />

      <Card padding="lg">
        <Group align="flex-end" grow>
          <TextInput
            label="Search"
            placeholder="Enter at least two characters"
            leftSection={<FaSearch size={14} />}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") setQuery("");
            }}
          />
          <Select
            label="Person type"
            placeholder="Everyone"
            clearable
            data={[
              { value: "student", label: "Students" },
              { value: "faculty", label: "Faculty" },
              { value: "staff", label: "Staff" },
            ]}
            value={kind}
            onChange={setKind}
          />
        </Group>
      </Card>

      {error && <ErrorState error={error} />}

      {!error && !enabled && (
        <Center mih={260}>
          <Stack align="center" gap="xs">
            <FaUsers size={28} color="var(--mantine-color-dimmed)" />
            <Text c="dimmed">Type a name or username to search the directory.</Text>
          </Stack>
        </Center>
      )}

      {!error && enabled && (isPending || isFetching) && (
        <Center mih={260}><Loader /></Center>
      )}

      {!error && enabled && !isPending && !isFetching && (
        <Card padding={0} mt="lg" withBorder>
          <Table.ScrollContainer minWidth={760}>
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Name</Table.Th>
                  <Table.Th>Username</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Department / Programme</Table.Th>
                  <Table.Th>Email</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {data?.results.map((person) => (
                  <Table.Tr key={person.user_id}>
                    <Table.Td>
                      <Text fw={600}>{person.display_name || person.username}</Text>
                      <Text size="xs" c="dimmed">ID {person.user_id}</Text>
                    </Table.Td>
                    <Table.Td>{person.username}</Table.Td>
                    <Table.Td><Badge variant="light">{person.kind}</Badge></Table.Td>
                    <Table.Td>
                      {person.department || person.programme || person.discipline || "-"}
                    </Table.Td>
                    <Table.Td>{person.email || "-"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {!data?.results.length && (
            <Text c="dimmed" ta="center" py="xl">No matching people found.</Text>
          )}
        </Card>
      )}
    </Container>
  );
}
