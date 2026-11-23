import { Badge, Card, Container, Text } from "@mantine/core";
import { FaUserCheck } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMemberships } from "../api/hooks";
import type { Membership } from "../api/types";
import { date } from "../components/format";
import { LoadMore } from "../components/LoadMore";
import { PageError } from "../components/PageError";

export default function MembershipsPage() {
  const mine = useMemberships();
  if (mine.error) return <PageError error={mine.error} />;

  return (
    <Container size="xl">
      <PageHeader title="My Club Memberships" subtitle="Your applications and where they stand" />
      <Card padding="lg">
        <DataTable<Membership>
          rows={mine.rows} loading={mine.loading} rowKey={(m) => m.id}
          columns={[
            { key: "club_name", header: "Club", render: (m) => <Text fw={600}>{m.club_name}</Text> },
            { key: "description", header: "Your application" },
            { key: "applied_at", header: "Applied", render: (m) => date(m.applied_at) },
            {
              key: "status", header: "Status",
              render: (m) => (
                <Badge variant="light" color={m.status === "confirmed" ? "green" : "blue"}>
                  {m.status}
                </Badge>
              ),
            },
            { key: "remarks", header: "Remarks", render: (m) => m.remarks || "—" },
          ]}
          empty={{
            icon: FaUserCheck, title: "No applications yet",
            description: "Open Clubs and apply to one to see it here.",
          }}
        />
        <LoadMore list={mine} />
      </Card>
    </Container>
  );
}
