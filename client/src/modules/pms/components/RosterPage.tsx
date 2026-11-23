import { Container } from "@mantine/core";
import { FaUsers } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReferenceData } from "../api/hooks";
import type { RosterEntry } from "../api/types";
import { ActionBar, type Runner, action, num } from "./ActionBar";
import { day } from "./format";

interface RosterQuery { data?: RosterEntry[]; isPending: boolean; error: unknown }

// A roster PCC_ADMIN maintains; a change ends the old entry and starts a new one.
export function RosterPage({ title, subtitle, who, roster, save, end }: {
  title: string;
  subtitle: string;
  who: string;
  roster: RosterQuery;
  save: Runner<{ user_id: number; domain_codes: string[] }>;
  end: Runner<number>;
}) {
  const ref = useReferenceData();
  const areas = (ref.data?.domains ?? []).map((d) => ({ value: d.code, label: d.label }));
  const add = action({ key: "add", label: `Add ${who}`, title: `Add or update a ${who}`,
    subtitle: "Adding someone already listed replaces their areas.", fields: [
      { name: "user_id", label: "Person", type: "person", required: true },
      { name: "domain_codes", label: "Technical areas", type: "multiselect", required: true,
        options: areas },
    ], submitLabel: "Save" }, save, (v) => ({ user_id: num(v.user_id),
    domain_codes: (v.domain_codes as string[]) ?? [] }));
  return (
    <Container size="xl" pt="md">
      <PageHeader title={title} subtitle={subtitle} action={<ActionBar actions={[add]} />} />
      {roster.error ? <ErrorState error={roster.error} /> : (
        <DataTable<RosterEntry>
          rows={roster.data ?? []} loading={roster.isPending} rowKey={(r) => r.id}
          empty={{ icon: FaUsers, title: `No ${who}s yet`,
            description: `Add the first ${who} to start assigning work.` }}
          columns={[
            { key: "name", header: "Name" },
            { key: "domain_codes", header: "Areas", render: (r) => r.domain_codes.join(", ") },
            { key: "workload", header: "Open items", render: (r) => String(r.workload) },
            { key: "valid_from", header: "Since", render: (r) => day(r.valid_from) },
            { key: "end", header: "", align: "right", render: (r) => (
              <ActionBar actions={[action({ key: `end-${r.id}`, label: "Remove", danger: true,
                title: `Remove ${r.name}`, subtitle: "Open work stays with them until reassigned.",
                fields: [], submitLabel: "Remove" }, end, () => r.id)]} />) },
          ]}
        />
      )}
    </Container>
  );
}
