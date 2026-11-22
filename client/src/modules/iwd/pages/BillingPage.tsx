import { useEffect, useState } from "react";
import { Badge, Button, Card, Container, Group, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { http, errorMessage } from "../../../lib/http";
import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import type { Complaint } from "../types";

export default function BillingPage() {
  const { can } = useAuth();
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown | null>(null);

  const fetchSettlementQueue = () => {
    setLoading(true);
    http
      .get("/iwd/complaints/")
      .then((res) => {
        const rows: Complaint[] = res.data.results || res.data;
        const billingQueue = rows.filter(
          (c) =>
            c.status === "Resolved" ||
            c.status === "Audit Pending" ||
            c.status === "Director Payment Approval Pending" ||
            c.status === "Accounts Settlement Pending" ||
            c.status === "Settled"
        );
        setComplaints(billingQueue);
        setError(null);
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSettlementQueue();
  }, []);

  const handleAudit = async (id: number, action: "validate" | "query") => {
    try {
      await http.post(`/iwd/complaints/${id}/audit/`, { action });
      notifications.show({ color: "teal", title: "Audit Recorded", message: `Action ${action} submitted.` });
      fetchSettlementQueue();
    } catch (err) {
      notifications.show({ color: "red", title: "Action Failed", message: errorMessage(err) });
    }
  };

  const handleDirectorApprove = async (id: number) => {
    try {
      await http.post(`/iwd/complaints/${id}/settle/`, { approve: true });
      notifications.show({ color: "teal", title: "Approved", message: "Director approved payment." });
      fetchSettlementQueue();
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
        title="Billing, Audit & Accounts Settlement"
        subtitle="Verification-guarded financial settlement for completed maintenance works"
      />

      <DataTable<Complaint>
        records={complaints}
        fetching={loading}
        totalRecords={complaints.length}
        recordsPerPage={10}
        page={1}
        onPageChange={() => {}}
        columns={[
          { accessor: "id", title: "#", width: 70 },
          { accessor: "category", title: "Category", width: 120 },
          { accessor: "location", title: "Location" },
          {
            accessor: "status",
            title: "Financial State",
            width: 220,
            render: (c) => (
              <Badge color={c.status === "Settled" ? "teal" : "blue"}>
                {c.status}
              </Badge>
            ),
          },
          {
            accessor: "actions",
            title: "Actions",
            width: 240,
            render: (c) => (
              <Group gap="xs">
                {c.status === "Audit Pending" && can("iwd.bill.review") && (
                  <Button size="xs" color="teal" onClick={() => handleAudit(c.id, "validate")}>
                    Validate Bill
                  </Button>
                )}
                {c.status === "Director Payment Approval Pending" && can("iwd.bill.review") && (
                  <Button size="xs" color="teal" onClick={() => handleDirectorApprove(c.id)}>
                    Sanction Payment
                  </Button>
                )}
                {c.status === "Accounts Settlement Pending" && can("iwd.bill.review") && (
                  <Button size="xs" color="teal" onClick={() => handleDirectorApprove(c.id)}>
                    Disburse & Settle
                  </Button>
                )}
              </Group>
            ),
          },
        ]}
      />
    </Container>
  );
}
