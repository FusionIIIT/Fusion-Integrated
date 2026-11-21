import { Badge, Card, Container, Group, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRequests } from "../api/hooks";
import { RequestActions } from "./RequestActions";
import { RequestComposer } from "./RequestComposer";
import { RequestDetails } from "./RequestDetails";

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

type RequestView = "all" | "leave" | "claims" | "appraisal" | "approvals" | "finance";
const titles: Record<RequestView, string> = {
  all: "HR Requests",
  leave: "Leave requests",
  claims: "LTC and CPDA claims",
  appraisal: "Annual appraisals",
  approvals: "Assigned approval queue",
  finance: "Accountant processing queue",
};

export default function RequestsPage({ view = "all" }: { view?: RequestView }) {
  const { data, error, isPending } = useRequests(
    view === "approvals" ? "approvals" : "all",
  );
  const requests = (data?.results ?? []).filter((item) => {
    if (view === "leave") return item.family === "leave";
    if (view === "claims" || view === "finance") {
      return ["ltc", "cpda"].includes(item.family);
    }
    if (view === "appraisal") return item.family === "appraisal";
    return true;
  });
  return (
    <Container size="xl">
      <PageHeader title={titles[view]}
        subtitle="Submit, track and review requests in your current acting role" />
      {["all", "leave", "claims", "appraisal"].includes(view)
        && <RequestComposer only={view === "all" ? undefined : view as "leave" | "claims" | "appraisal"} />}
      {error && <ErrorState error={error} />}
      {isPending && <Text c="dimmed">Loading request statuses...</Text>}
      {data && (
        <Card withBorder>
          {requests.length === 0
            ? <Text c="dimmed">There are no HR requests in your current role's scope.</Text>
            : <Table.ScrollContainer minWidth={600}>
              <Table striped highlightOnHover>
                <Table.Thead><Table.Tr>
                  <Table.Th>Request</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Submitted</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>
                  {requests.map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td>#{item.id}</Table.Td>
                      <Table.Td>{humanize(item.family)} {humanize(item.subtype)}</Table.Td>
                      <Table.Td><Badge variant="light">{humanize(item.state)}</Badge></Table.Td>
                      <Table.Td>{item.submitted_at
                        ? new Date(item.submitted_at).toLocaleDateString()
                        : "Not submitted"}</Table.Td>
                      <Table.Td><Group gap="xs">
                        <RequestDetails id={item.id} />
                        <RequestActions request={item} />
                      </Group></Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>}
        </Card>
      )}
    </Container>
  );
}
