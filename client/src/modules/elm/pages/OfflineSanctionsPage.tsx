import { useState } from "react";
import { Alert, Button, Card, Grid, Group, NumberInput, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes } from "../api/hooks";
import { http } from "../../../lib/http";

export default function OfflineSanctionsPage() {
  const { data: leaveTypes = [] } = useLeaveTypes();

  const [employeeId, setEmployeeId] = useState<number | "">("");
  const [leaveTypeId, setLeaveTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [orderNo, setOrderNo] = useState("");
  const [orderDate, setOrderDate] = useState("");
  const [sanctionRole, setSanctionRole] = useState("Director");
  const [remarks, setRemarks] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId || !leaveTypeId || !startDate || !endDate || !orderNo || !orderDate) return;

    setSubmitting(true);
    setIsSuccess(false);
    setErrorMsg("");

    try {
      await http.post("/elm/admin/offline-leave", {
        employee_id: Number(employeeId),
        leave_type_id: Number(leaveTypeId),
        start_date: startDate,
        end_date: endDate,
        sanction_order_no: orderNo,
        sanction_order_date: orderDate,
        sanctioned_by_role: sanctionRole,
        remarks,
      });
      setIsSuccess(true);
      setEmployeeId("");
      setLeaveTypeId(null);
      setStartDate("");
      setEndDate("");
      setOrderNo("");
      setOrderDate("");
      setRemarks("");
    } catch (err: any) {
      setErrorMsg(err.response?.data?.error?.message || "Failed to record offline leave.");
    } finally {
      setSubmitting(false);
    }
  };

  const typeOptions = leaveTypes.map((t) => ({
    value: String(t.id),
    label: `${t.code} — ${t.name}`,
  }));

  return (
    <div>
      <PageHeader
        title="Offline Sanction Synchronization"
        subtitle="Retrospectively synchronize leave sanctioned through paper/offline orders (EL-UC-016, BR-EL-029)"
      />

      <form onSubmit={handleSubmit}>
        <Stack gap="lg" maw={700}>
          {isSuccess && (
            <Alert color="green" title="Record Synchronized">
              Offline-sanctioned leave has been recorded and employee balance updated without initiating a second approval workflow.
            </Alert>
          )}

          {errorMsg && (
            <Alert color="red" title="Error">
              {errorMsg}
            </Alert>
          )}

          <Card withBorder padding="md" radius="sm">
            <Stack gap="md">
              <Text fw={600} size="sm">1. Employee & Leave Details</Text>
              <NumberInput
                label="Employee ID"
                placeholder="Enter employee ID"
                value={employeeId}
                onChange={(val) => setEmployeeId(val === "" ? "" : Number(val))}
                required
              />
              <Select
                label="Leave Category"
                placeholder="Select category"
                data={typeOptions}
                value={leaveTypeId}
                onChange={setLeaveTypeId}
                required
              />
              <Grid>
                <Grid.Col span={6}>
                  <TextInput
                    label="Start Date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.currentTarget.value)}
                    required
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="End Date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.currentTarget.value)}
                    required
                  />
                </Grid.Col>
              </Grid>
            </Stack>
          </Card>

          <Card withBorder padding="md" radius="sm">
            <Stack gap="md">
              <Text fw={600} size="sm">2. Sanction Order Evidence</Text>
              <Grid>
                <Grid.Col span={6}>
                  <TextInput
                    label="Sanction Order / Dispatch No."
                    placeholder="e.g. IIITDMJ/ESTT/2026/842"
                    value={orderNo}
                    onChange={(e) => setOrderNo(e.currentTarget.value)}
                    required
                  />
                </Grid.Col>
                <Grid.Col span={6}>
                  <TextInput
                    label="Order Date"
                    type="date"
                    value={orderDate}
                    onChange={(e) => setOrderDate(e.currentTarget.value)}
                    required
                  />
                </Grid.Col>
              </Grid>
              <Select
                label="Sanctioned By (Competent Authority Role)"
                data={[
                  { value: "Director", label: "Director" },
                  { value: "Registrar", label: "Registrar" },
                  { value: "Dean", label: "Dean" },
                  { value: "Unit Head", label: "Unit Head / HOD" },
                ]}
                value={sanctionRole}
                onChange={(val) => setSanctionRole(val || "Director")}
                required
              />
              <Textarea
                label="Reference Remarks / Notes"
                placeholder="Reason offline route was used (e.g. medical emergency, server unavailability)..."
                value={remarks}
                onChange={(e) => setRemarks(e.currentTarget.value)}
              />
            </Stack>
          </Card>

          <Group justify="flex-end">
            <Button type="submit" loading={submitting}>
              Synchronize Record
            </Button>
          </Group>
        </Stack>
      </form>
    </div>
  );
}
