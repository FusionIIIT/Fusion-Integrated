import { useState } from "react";
import {
  Badge,
  Button,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaShieldAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAddBlacklist, useBlacklist, useSafeList } from "../api/hooks";
import type { BlacklistEntry } from "../api/types";

export default function BlacklistPage() {
  const { data: entries, isPending, error } = useBlacklist();
  const addEntry = useAddBlacklist();
  const safeList = useSafeList();

  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("AADHAAR");
  const [docNumber, setDocNumber] = useState("");
  const [phone, setPhone] = useState("");
  const [reason, setReason] = useState("");

  const [safeListing, setSafeListing] = useState<BlacklistEntry | null>(null);
  const [safeHours, setSafeHours] = useState("24");
  const [safeReason, setSafeReason] = useState("");

  if (error)
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );

  function handleAddSubmit() {
    addEntry.mutate(
      {
        name,
        id_document_type: docType,
        id_document_number: docNumber,
        phone,
        reason,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "red",
            title: "Blacklist Entry Added",
            message: `${name} has been blacklisted.`,
          });
          setAdding(false);
          setName("");
          setDocNumber("");
          setPhone("");
          setReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Failed to Add Entry",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleSafeListSubmit() {
    if (!safeListing) return;
    safeList.mutate(
      {
        id: safeListing.id,
        hours: parseInt(safeHours, 10),
        reason: safeReason,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "teal",
            title: "Safe-list Exemption Active",
            message: `${safeListing.name} granted safe-list pass for ${safeHours} hours.`,
          });
          setSafeListing(null);
          setSafeReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Safe-list Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Security Blacklist & Safe-list Registry"
          subtitle="Manage security watchlists, deny prohibited entries, or grant temporary safe-list exemptions."
          action={
            <Button leftSection={<FaPlus />} color="red" onClick={() => setAdding(true)}>
              Add to Blacklist
            </Button>
          }
        />

        <DataTable
          loading={isPending}
          rows={entries ?? []}
          rowKey={(e) => e.id}
          empty={{ title: "No individuals currently blacklisted." }}
          columns={[
            {
              key: "name",
              header: "Subject Name",
              render: (e: BlacklistEntry) => (
                <Stack gap={2}>
                  <Text fw={600}>{e.name}</Text>
                  <Text size="xs" c="dimmed">
                    Phone: {e.phone || "N/A"}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "doc",
              header: "ID Document",
              render: (e: BlacklistEntry) => `${e.id_document_type} #${e.id_document_number}`,
            },
            {
              key: "reason",
              header: "Reason / Justification",
              render: (e: BlacklistEntry) => <Text size="sm">{e.reason}</Text>,
            },
            {
              key: "status",
              header: "Status",
              render: (e: BlacklistEntry) => (
                <Badge
                  color={
                    e.status === "ACTIVE" ? "red" : e.status === "SAFE_LISTED" ? "teal" : "gray"
                  }
                >
                  {e.status}
                </Badge>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              render: (e: BlacklistEntry) =>
                e.status === "ACTIVE" ? (
                  <Button
                    size="xs"
                    color="teal"
                    variant="light"
                    leftSection={<FaShieldAlt />}
                    onClick={() => setSafeListing(e)}
                  >
                    Grant Safe-list
                  </Button>
                ) : (
                  <Text size="xs" c="dimmed">
                    Exempt until{" "}
                    {e.safe_list_until ? new Date(e.safe_list_until).toLocaleDateString() : ""}
                  </Text>
                ),
            },
          ]}
        />

        {/* Modal: Add to Blacklist */}
        <Modal
          opened={adding}
          onClose={() => setAdding(false)}
          title="Add Individual to Blacklist"
          size="md"
        >
          <Stack gap="sm">
            <TextInput
              label="Full Name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Select
              label="ID Document Type"
              data={["AADHAAR", "PAN", "PASSPORT", "VOTER_ID", "DRIVING_LICENSE", "INSTITUTE_ID"]}
              value={docType}
              onChange={(v) => setDocType(v ?? "AADHAAR")}
            />
            <TextInput
              label="ID Document Number"
              required
              value={docNumber}
              onChange={(e) => setDocNumber(e.target.value)}
            />
            <TextInput
              label="Phone Number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <TextInput
              label="Reason for Blacklisting"
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setAdding(false)}>
                Cancel
              </Button>
              <Button color="red" loading={addEntry.isPending} onClick={handleAddSubmit}>
                Confirm Blacklisting
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Grant Safe-list */}
        <Modal
          opened={!!safeListing}
          onClose={() => setSafeListing(null)}
          title="Grant Temporary Safe-list Exemption"
          size="sm"
        >
          <Stack gap="sm">
            <Text size="sm">
              Granting temporary safe-list for <b>{safeListing?.name}</b>:
            </Text>
            <Select
              label="Exemption Duration"
              data={[
                { value: "4", label: "4 Hours" },
                { value: "12", label: "12 Hours" },
                { value: "24", label: "24 Hours (1 Day)" },
                { value: "48", label: "48 Hours (2 Days)" },
              ]}
              value={safeHours}
              onChange={(v) => setSafeHours(v ?? "24")}
            />
            <TextInput
              label="Exemption Justification"
              required
              value={safeReason}
              onChange={(e) => setSafeReason(e.target.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setSafeListing(null)}>
                Cancel
              </Button>
              <Button color="teal" loading={safeList.isPending} onClick={handleSafeListSubmit}>
                Activate Safe-list
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
