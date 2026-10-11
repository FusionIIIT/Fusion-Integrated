import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeave } from "../api/hooks";

export default function ApplyPage() {
  const navigate = useNavigate();
  const applyMut = useApplyLeave();

  const [category, setCategory] = useState<string>("CL");
  const [startsOn, setStartsOn] = useState<string>("");
  const [endsOn, setEndsOn] = useState<string>("");
  const [half, setHalf] = useState<string>("none");
  const [reason, setReason] = useState<string>("");
  const [evidenceRef, setEvidenceRef] = useState<string>("");
  const [substituteId, setSubstituteId] = useState<number | undefined>(undefined);
  const [isStationLeaving, setIsStationLeaving] = useState<boolean>(false);
  const [destination, setDestination] = useState<string>("");
  const [emergencyContact, setEmergencyContact] = useState<string>("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!category || !startsOn || !endsOn || !reason) {
      notifications.show({
        color: "yellow",
        title: "Required Fields Missing",
        message: "Please fill in category, start date, end date, and reason.",
      });
      return;
    }

    applyMut.mutate(
      {
        category,
        starts_on: startsOn,
        ends_on: endsOn,
        half,
        reason,
        evidence_reference: evidenceRef || undefined,
        substitute_user_id: substituteId || undefined,
        station: isStationLeaving
          ? { destination, emergency_contact: emergencyContact }
          : undefined,
      },
      {
        onSuccess: (req) => {
          notifications.show({
            color: "green",
            title: "Leave Application Submitted",
            message: `Your request #${req.id} has been submitted successfully.`,
          });
          navigate("/leave/mine");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Application Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new leave application with academic/work arrangements"
      />

      <Card padding="lg" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              required
              data={[
                { value: "CL", label: "Casual Leave (CL)" },
                { value: "RH", label: "Restricted Holiday (RH)" },
                { value: "EL", label: "Earned Leave (EL)" },
                { value: "SCL", label: "Special Casual Leave (SCL)" },
                { value: "COL", label: "Commuted Leave (COL)" },
                { value: "VL", label: "Vacation Leave (VL)" },
                { value: "ML", label: "Maternity Leave (ML)" },
                { value: "PL", label: "Paternity Leave (PL)" },
                { value: "CCL", label: "Child Care Leave (CCL)" },
                { value: "SL", label: "Station Leave (SL)" },
                { value: "LND", label: "Leave Not Due (LND)" },
                { value: "EOL", label: "Extraordinary Leave (EOL)" },
              ]}
              value={category}
              onChange={(val) => setCategory(val ?? "CL")}
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                required
                value={startsOn}
                onChange={(e) => setStartsOn(e.currentTarget.value)}
              />
              <TextInput
                label="End Date"
                type="date"
                required
                value={endsOn}
                onChange={(e) => setEndsOn(e.currentTarget.value)}
              />
            </Group>

            {category === "CL" && (
              <Select
                label="Half Day Option"
                data={[
                  { value: "none", label: "Full Day" },
                  { value: "first_half", label: "First Half (Forenoon)" },
                  { value: "second_half", label: "Second Half (Afternoon)" },
                ]}
                value={half}
                onChange={(val) => setHalf(val ?? "none")}
              />
            )}

            <NumberInput
              label="Substitute User ID (Optional standing-in arrangement)"
              placeholder="e.g. 102"
              value={substituteId}
              onChange={(val) => setSubstituteId(typeof val === "number" ? val : undefined)}
            />

            <TextInput
              label="Evidence / Medical Certificate Reference"
              placeholder="e.g. MED-2026-001 (required for SCL, ML, CCL, SL, LND)"
              value={evidenceRef}
              onChange={(e) => setEvidenceRef(e.currentTarget.value)}
            />

            <Textarea
              label="Reason for Leave"
              required
              minRows={3}
              placeholder="State the purpose of your leave..."
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
            />

            <Checkbox
              label="Leaving Station (Station Permission required)"
              checked={isStationLeaving}
              onChange={(e) => setIsStationLeaving(e.currentTarget.checked)}
            />

            {isStationLeaving && (
              <Group grow>
                <TextInput
                  label="Destination Address / City"
                  required={isStationLeaving}
                  value={destination}
                  onChange={(e) => setDestination(e.currentTarget.value)}
                />
                <TextInput
                  label="Emergency Contact Number"
                  required={isStationLeaving}
                  value={emergencyContact}
                  onChange={(e) => setEmergencyContact(e.currentTarget.value)}
                />
              </Group>
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/leave/mine")}>Cancel</Button>
              <Button type="submit" loading={applyMut.isPending}>Submit Application</Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
