import { useMemo, useState } from "react";
import { Button, Container, Group, Select, Stack, Text, TextInput } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

type UserRow = Record<string, unknown> & { username: string };
type UserResponse = UserRow[] | { results?: UserRow[] };
type UserType = "student" | "faculty" | "staff";

const FILTERS = [
  ["gender", "Gender"],
  ["programme", "Programme"],
  ["batch", "Batch"],
  ["discipline", "Discipline"],
  ["category", "Category"],
  ["designation", "Designation"],
] as const;

function display(value: unknown) {
  return typeof value === "string" || typeof value === "number" ? String(value) : "—";
}

function rowsFrom(response: UserResponse): UserRow[] {
  const rows = Array.isArray(response) ? response : response.results ?? [];
  return rows.filter((row): row is UserRow =>
    typeof row?.username === "string" && row.username.trim().length > 0);
}

export default function UsersPage() {
  const [type, setType] = useState<UserType | null>(null);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const query = useQuery({
    queryKey: ["superadmin", "users", type, filters],
    queryFn: async () => {
      const response = await http.get<UserResponse>("/superadmin/users", {
        params: { type, ...filters },
      });
      return rowsFrom(response.data);
    },
    enabled: type !== null,
    staleTime: 30_000,
  });

  const visibleRows = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase();
    return (query.data ?? []).filter((row) =>
      !needle || row.username.toLocaleLowerCase().includes(needle));
  }, [query.data, search]);

  function setFilter(key: string, value: string) {
    setFilters((previous) => {
      const next = { ...previous };
      if (value.trim()) next[key] = value.trim();
      else delete next[key];
      return next;
    });
  }

  function clearFilters() {
    setFilters({});
    setSearch("");
  }

  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;

  const columns = [
    { key: "username", header: "Username", render: (row: UserRow) => display(row.username) },
    { key: "first_name", header: "First name", render: (row: UserRow) => display(row.first_name) },
    { key: "last_name", header: "Last name", render: (row: UserRow) => display(row.last_name) },
    { key: "email", header: "Email", render: (row: UserRow) => display(row.email) },
    { key: "designation", header: "Designation", render: (row: UserRow) => display(row.designation) },
    { key: "type", header: "Type", render: (row: UserRow) => display(row.type) },
  ];

  return (
    <Container size="xl">
      <PageHeader title="Users" subtitle="Search the institute directory" />
      <Stack>
        <Group align="end" wrap="wrap">
          <Select
            label="User type"
            placeholder="Choose a user type"
            aria-label="Filter by user type"
            value={type}
            onChange={(value) => setType(value as UserType | null)}
            data={[
              { value: "student", label: "Student" },
              { value: "faculty", label: "Faculty" },
              { value: "staff", label: "Staff" },
            ]}
            clearable
          />
          <TextInput
            label="Search username"
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
            disabled={type === null}
          />
          {FILTERS.map(([key, label]) => (
            <TextInput
              key={key}
              label={label}
              value={filters[key] ?? ""}
              onChange={(event) => setFilter(key, event.currentTarget.value)}
              disabled={type === null}
            />
          ))}
          <Button variant="default" onClick={clearFilters}>Clear filters</Button>
        </Group>
        {type === null ? (
          <Text c="dimmed">Choose Student, Faculty, or Staff to load directory records.</Text>
        ) : (
          <DataTable<UserRow>
            rows={visibleRows}
            columns={columns}
            loading={query.isPending}
            rowKey={(row) => row.username}
            minWidth={900}
            empty={{ title: "No users found", description: "Change the type or filters and try again." }}
          />
        )}
      </Stack>
    </Container>
  );
}
