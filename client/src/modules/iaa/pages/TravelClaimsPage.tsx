import { useState } from "react";
import {
  Button,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  NumberInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { useTravelClaims, useCreateTravelClaim } from "../api/hooks";
import type { TAClaim } from "../api/types";

export default function TravelClaimsPage() {
  const { data: claims, isPending, error } = useTravelClaims();
  const createMutation = useCreateTravelClaim();
  const { can } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [department, setDepartment] = useState("CSE");
  const [purpose, setPurpose] = useState("");
  const [source, setSource] = useState("IIITDM Jabalpur");
  const [destination, setDestination] = useState("");
  const [departureDate, setDepartureDate] = useState("2026-11-05");
  const [arrivalDate, setArrivalDate] = useState("2026-11-08");
  const [amount, setAmount] = useState<number>(5000);

  const canCreate = can("iaa.travel.create");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync({
        department,
        purpose,
        departure_date: departureDate,
        arrival_date: arrivalDate,
        source_location: source,
        destination_location: destination,
        claimed_amount: amount,
      });
      notifications.show({ title: "Claim Submitted", message: "TA claim submitted successfully." });
      setModalOpen(false);
      setPurpose("");
      setDestination("");
      setAmount(5000);
    } catch (e: unknown) {
      notifications.show({
        title: "Error",
        message: e instanceof Error ? e.message : "Submission failed",
        color: "red",
      });
    }
  };

  const columns: Column<TAClaim>[] = [
    { key: "id", header: "ID", render: (c) => `#TA-${c.id}` },
    { key: "purpose", header: "Purpose", render: (c) => c.purpose },
    { key: "department", header: "Department", render: (c) => c.department },
    {
      key: "route",
      header: "Journey",
      render: (c) => `${c.source_location} ➔ ${c.destination_location}`,
    },
    { key: "claimed_amount", header: "Claimed Amount", render: (c) => `₹${c.claimed_amount}` },
    { key: "status", header: "Status", render: (c) => <StatusBadge status={c.status} /> },
  ];

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Travel Allowance (TA) Claims"
          subtitle="Submit official travel expense claims and track verification/approval progress."
          action={
            canCreate ? (
              <Button onClick={() => setModalOpen(true)}>Submit TA Claim</Button>
            ) : undefined
          }
        />

        <DataTable
          rows={claims || []}
          columns={columns}
          loading={isPending}
          rowKey={(c) => c.id}
          empty={{ title: "No travel claims found." }}
        />

        <Modal
          opened={modalOpen}
          onClose={() => setModalOpen(false)}
          title={<Text fw={600}>Submit Travel Allowance Claim</Text>}
          centered
        >
          <Stack gap="sm">
            <Select
              label="Department"
              data={["CSE", "ECE", "ME", "Design", "Natural Sciences"]}
              value={department}
              onChange={(val) => setDepartment(val || "CSE")}
              required
            />
            <TextInput
              label="Purpose"
              placeholder="e.g. Attending IEEE Conference"
              value={purpose}
              onChange={(e) => setPurpose(e.currentTarget.value)}
              required
            />
            <Group grow>
              <TextInput
                label="Source"
                value={source}
                onChange={(e) => setSource(e.currentTarget.value)}
                required
              />
              <TextInput
                label="Destination"
                placeholder="e.g. New Delhi"
                value={destination}
                onChange={(e) => setDestination(e.currentTarget.value)}
                required
              />
            </Group>
            <Group grow>
              <TextInput
                label="Departure Date"
                type="date"
                value={departureDate}
                onChange={(e) => setDepartureDate(e.currentTarget.value)}
                required
              />
              <TextInput
                label="Arrival Date"
                type="date"
                value={arrivalDate}
                onChange={(e) => setArrivalDate(e.currentTarget.value)}
                required
              />
            </Group>
            <NumberInput
              label="Total Claimed Amount (₹)"
              value={amount}
              onChange={(val) => setAmount(Number(val) || 0)}
              min={1}
              required
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} loading={createMutation.isPending}>
                Submit Claim
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
