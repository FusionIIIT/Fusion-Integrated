import { useQuery } from "@tanstack/react-query";
import { Badge, Container } from "@mantine/core";

import { http } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

type Role = Record<string, unknown>;
type RoleResponse = Role[] | { results?: Role[] };

function rolesFrom(response: RoleResponse): Role[] {
  return Array.isArray(response) ? response : response.results ?? [];
}

function value(row: Role, key: string) {
  const item = row[key];
  if (typeof item === "string" || typeof item === "number") return String(item);
  if (typeof item === "boolean") return item ? "Yes" : "No";
  return "—";
}

export default function RolesPage() {
  const query = useQuery({
    queryKey: ["superadmin", "roles"],
    queryFn: async () => rolesFrom((await http.get<RoleResponse>("/superadmin/roles")).data),
    staleTime: 60_000,
  });

  if (query.error) return <Container size="xl"><ErrorState error={query.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Roles" subtitle="View role metadata available in the identity service" />
      <DataTable<Role>
        rows={query.data ?? []}
        columns={[
          { key: "name", header: "Role", render: (row) => value(row, "name") },
          { key: "designation", header: "Designation", render: (row) => value(row, "designation") },
          { key: "user_type", header: "User type", render: (row) => value(row, "user_type") },
          { key: "status", header: "Status", render: (row) => <Badge variant="light">{value(row, "status")}</Badge> },
        ]}
        loading={query.isPending}
        rowKey={(row) => value(row, "id") !== "—" ? value(row, "id") : value(row, "name")}
        minWidth={720}
        empty={{ title: "No roles found", description: "The identity service returned no role records." }}
      />
    </Container>
  );
}
