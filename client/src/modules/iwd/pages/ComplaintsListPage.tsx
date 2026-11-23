import { useEffect, useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, TextInput } from "@mantine/core";
import { Link, useNavigate } from "react-router-dom";
import { FaPlus, FaSearch } from "react-icons/fa";

import { http, errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import type { Complaint } from "../types";

export default function ComplaintsListPage() {
  const navigate = useNavigate();
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    http
      .get("/iwd/complaints/")
      .then((res) => {
        setComplaints(res.data.results || res.data);
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const filtered = complaints.filter(
    (c) =>
      c.location.toLowerCase().includes(search.toLowerCase()) ||
      c.category.toLowerCase().includes(search.toLowerCase()) ||
      c.status.toLowerCase().includes(search.toLowerCase()) ||
      c.remarks.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Container size="xl">
      <PageHeader
        title="Maintenance Complaints"
        subtitle="Institute Work Department maintenance and repair requests"
        action={
          <Button
            component={Link}
            to="/iwd/submit"
            leftSection={<FaPlus size={12} />}
          >
            Submit Complaint
          </Button>
        }
      />

      <Stack gap="md" mt="md">
        <TextInput
          placeholder="Filter complaints by category, location, status..."
          leftSection={<FaSearch size={14} />}
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
        />

        <DataTable<Complaint>
          rows={filtered}
          loading={loading}
          rowKey={(c) => c.id}
          empty={{ title: "No complaints found", description: "Submit a new maintenance request above." }}
          columns={[
            {
              key: "id",
              header: "#",
              render: (c) => (
                <Text
                  fw={600}
                  c="blue"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/iwd/complaints/${c.id}`)}
                >
                  #{c.id}
                </Text>
              ),
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
              key: "urgency",
              header: "Urgency",
              render: (c) => (
                <Badge
                  color={
                    c.urgency === "Urgent"
                      ? "red"
                      : c.urgency === "High"
                      ? "orange"
                      : "blue"
                  }
                >
                  {c.urgency}
                </Badge>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (c) => (
                <Badge
                  color={
                    c.status === "Resolved" || c.status === "Settled"
                      ? "teal"
                      : c.status.includes("Pending")
                      ? "yellow"
                      : "gray"
                  }
                >
                  {c.status}
                </Badge>
              ),
            },
            {
              key: "created_at",
              header: "Submitted",
              render: (c) => new Date(c.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Stack>
    </Container>
  );
}
