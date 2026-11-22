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
          records={filtered}
          fetching={loading}
          totalRecords={filtered.length}
          recordsPerPage={10}
          page={1}
          onPageChange={() => {}}
          onRowClick={({ record }) => navigate(`/iwd/complaints/${record.id}`)}
          columns={[
            { accessor: "id", title: "#", width: 70 },
            { accessor: "category", title: "Category", width: 120 },
            { accessor: "location", title: "Location" },
            {
              accessor: "urgency",
              title: "Urgency",
              width: 110,
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
              accessor: "status",
              title: "Status",
              width: 180,
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
              accessor: "created_at",
              title: "Submitted",
              width: 140,
              render: (c) => new Date(c.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Stack>
    </Container>
  );
}
