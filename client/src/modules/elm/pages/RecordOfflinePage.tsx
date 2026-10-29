import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Grid,
  Group,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaFileImport } from "react-icons/fa";


import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRecordOffline } from "../api/hooks";
import type { LeaveCategory } from "../api/types";

export default function RecordOfflinePage() {
  const recordMutation = useRecordOffline();

  const [targetUserId, setTargetUserId] = useState<number | string>("");
  const [category, setCategory] = useState<LeaveCategory>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reference, setReference] = useState("");
  const [purpose, setPurpose] = useState("");
  const [half, setHalf] = useState<"full" | "first_half" | "second_half">("full");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!targetUserId || !startDate || !endDate || !reference) {
      notifications.show({
        color: "red",
        title: "Required Fields",
        message: "Please specify target user, dates, category, and official reference.",
      });
      return;
    }

    recordMutation.mutate(
      {
        target_user_id: Number(targetUserId),
        category,
        start_date: startDate,
        end_date: endDate,
        offline_reference: reference,
        purpose,
        half,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "teal",
            title: "Offline Sanction Recorded",
            message: `Recorded ${data.category} leave for User #${data.user_id} (Dispatch: ${reference}).`,
          });
          setTargetUserId("");
          setStartDate("");
          setEndDate("");
          setReference("");
          setPurpose("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Recording Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Record Offline Sanction"
        subtitle="Log leaves approved offline via physical memos or executive orders (BR-EL-029)"
      />

      <Card padding="xl" radius="md" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="lg">
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <NumberInput
                  label="Employee User ID"
                  placeholder="e.g. 101"
                  value={targetUserId}
                  onChange={setTargetUserId}
                  min={1}
                  required
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Category"
                  data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
                  value={category}
                  onChange={(val) => setCategory((val as LeaveCategory) || "CL")}
                  required
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="Start Date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="End Date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>

              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Day Portion"
                  data={[
                    { value: "full", label: "Full Day" },
                    { value: "first_half", label: "First Half" },
                    { value: "second_half", label: "Second Half" },
                  ]}
                  value={half}
                  onChange={(val) => setHalf((val as "full" | "first_half" | "second_half") || "full")}
                />
              </Grid.Col>

              <Grid.Col span={12}>
                <TextInput
                  label="Official Dispatch / Approval Reference"
                  placeholder="e.g. IIITDMJ/DIR/OFFLINE/2026/042"
                  value={reference}
                  onChange={(e) => setReference(e.currentTarget.value)}
                  required
                />
              </Grid.Col>


              <Grid.Col span={12}>
                <Textarea
                  label="Purpose / Memo Details"
                  value={purpose}
                  onChange={(e) => setPurpose(e.currentTarget.value)}
                  minRows={3}
                />
              </Grid.Col>
            </Grid>

            <Group justify="flex-end" mt="md">
              <Button
                type="submit"
                leftSection={<FaFileImport />}
                loading={recordMutation.isPending}
              >
                Record Sanction
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
