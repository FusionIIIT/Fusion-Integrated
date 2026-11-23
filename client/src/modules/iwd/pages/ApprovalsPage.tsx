import { useEffect, useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";

import { http, errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import type { Complaint } from "../types";

export default function ApprovalsPage() {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);

  const fetchPending = () => {
    setLoading(true);
    http
      .get("/iwd/complaints/")
      .then((res) => {
        const rows: Complaint[] = res.data.results || res.data;
        const pending = rows.filter((c) =>
          c.status.includes("Pending") || c.status.includes("Review")
        );
        setComplaints(pending);
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleLowCost = async (id: number, approve: boolean) => {
    try {
      await http.post(`/iwd/complaints/${id}/review-low-cost/`, { approve });
      notifications.show({ color: "teal", title: "Success", message: "Low-cost estimate reviewed." });
      fetchPending();
    } catch (err) {
      notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) });
    }
  };

  if (error) {
    return <Container size="xl"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Approvals Inbox"
        subtitle="Review repair estimates requiring administrative or committee approvals"
      />

      <DataTable<Complaint>
        rows={complaints}
        loading={loading}
        rowKey={(c) => c.id}
        empty={{ title: "No pending approvals", description: "All estimates and escalations have been processed." }}
        columns={[
          {
            key: "id",
            header: "#",
            render: (c) => `#${c.id}`,
          },
          {
            key: "category",
            header: "Category",
            render: (c) => c.category,
          },
          {
            key: "location",
            header: "Location",
            render: (c) => c.location,
          },
          {
            key: "status",
            header: "Approval Stage",
            render: (c) => <Badge color="yellow">{c.status}</Badge>,
          },
          {
            key: "actions",
            header: "Actions",
            render: (c) => (
              <Group gap="xs">
                {c.status === "Low-Cost Review Pending" && (
                  <>
                    <Button size="xs" color="teal" onClick={() => handleLowCost(c.id, true)}>
                      Approve
                    </Button>
                    <Button size="xs" color="red" variant="outline" onClick={() => handleLowCost(c.id, false)}>
                      Reject
                    </Button>
                  </>
                )}
                <Button size="xs" variant="light" component={Link} to={`/iwd/complaints/${c.id}`}>
                  View Details
                </Button>
              </Group>
            ),
          },
        ]}
      />
    </Container>
  );
}
