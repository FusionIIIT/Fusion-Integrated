import React, { useState, useEffect } from "react";
import {
  Container,
  Card,
  Title,
  Text,
  SimpleGrid,
  Badge,
  Button,
  Group,
  Progress,
  Paper,
  Divider,
  Loader,
  Center,
  Stack,
  Modal,
  TextInput,
  NumberInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaChartPie, FaExchangeAlt, FaShieldAlt } from "react-icons/fa";

interface BalanceItem {
  id: number;
  username: string;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  balance: string;
  credited: string;
  utilized: string;
}

export default function LeaveBalancesPage() {
  const [balances, setBalances] = useState<BalanceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Conversion Modal
  const [conversionModalOpen, setConversionModalOpen] = useState<boolean>(false);
  const [facultyUsername, setFacultyUsername] = useState<string>("");
  const [conversionYear, setConversionYear] = useState<number>(new Date().getFullYear());
  const [converting, setConverting] = useState<boolean>(false);

  const fetchBalances = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/leave/balances/");
      if (res.ok) {
        const data = await res.json();
        setBalances(data.results || data);
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to load leave balances.", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBalances();
  }, []);

  const handleConvertVl = async () => {
    if (!facultyUsername) return;
    setConverting(true);
    try {
      const res = await fetch("/api/v1/leave/convert-vl-to-el/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          faculty_username: facultyUsername,
          year: conversionYear,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        notifications.show({
          title: "Year-End Conversion Complete",
          message: `Successfully converted ${data.converted_el_days} EL days (at 2 VL : 1 EL) for ${data.faculty_username} (BR-EL-007, BR-EL-008).`,
          color: "teal",
        });
        setConversionModalOpen(false);
        fetchBalances();
      } else {
        const err = await res.json();
        notifications.show({ title: "Error", message: err.error, color: "red" });
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to execute conversion.", color: "red" });
    } finally {
      setConverting(false);
    }
  };

  return (
    <Container size="xl" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Annual Leave Balances</Title>
          <Text c="dimmed" size="sm">
            Entitlements, utilization, and carry-forward rules per category (BR-EL-002 to BR-EL-009).
          </Text>
        </div>
        <Group>
          <Button
            leftSection={<FaExchangeAlt size={14} />}
            color="violet"
            variant="light"
            onClick={() => setConversionModalOpen(true)}
          >
            Year-End VL to EL Conversion
          </Button>
          <FaChartPie size={28} color="#228be6" />
        </Group>
      </Group>

      {loading ? (
        <Center py="xl">
          <Loader size="lg" />
        </Center>
      ) : balances.length === 0 ? (
        <Paper p="xl" withBorder radius="md">
          <Text ta="center" c="dimmed">
            No balance records found for the current academic session.
          </Text>
        </Paper>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
          {balances.map((item) => {
            const credited = parseFloat(item.credited) || 1;
            const utilized = parseFloat(item.utilized) || 0;
            const remaining = parseFloat(item.balance) || 0;
            const percent = Math.min(100, Math.round((utilized / credited) * 100));

            const isCarryForward = ["EL", "COL"].includes(item.leave_type_code);

            return (
              <Card key={item.id} shadow="sm" padding="lg" radius="md" withBorder>
                <Group justify="space-between" mb="xs">
                  <Badge size="lg" color="blue" variant="filled">
                    {item.leave_type_code}
                  </Badge>
                  <Badge color={isCarryForward ? "teal" : "gray"} variant="light">
                    {isCarryForward ? "Carries Forward" : "Lapses at Year-End"}
                  </Badge>
                </Group>

                <Text fw={600} size="md" mb="xs">
                  {item.leave_type_name}
                </Text>

                <Group justify="space-between" align="baseline" my="sm">
                  <Text size="xs" c="dimmed">
                    Remaining
                  </Text>
                  <Text fw={700} size="xl" c={remaining > 0 ? "teal" : "red"}>
                    {remaining} Days
                  </Text>
                </Group>

                <Progress value={percent} color={percent > 80 ? "red" : "blue"} size="sm" radius="xl" mb="xs" />

                <Divider my="xs" />

                <Group justify="space-between">
                  <Text size="xs" c="dimmed">
                    Credited: <b>{item.credited}</b>
                  </Text>
                  <Text size="xs" c="dimmed">
                    Utilized: <b>{item.utilized}</b>
                  </Text>
                  <Text size="xs" c="dimmed">
                    Year: <b>{item.year}</b>
                  </Text>
                </Group>
              </Card>
            );
          })}
        </SimpleGrid>
      )}

      {/* Year-End Conversion Modal */}
      <Modal
        opened={conversionModalOpen}
        onClose={() => setConversionModalOpen(false)}
        title="Faculty Vacation Leave to Earned Leave Conversion (BR-EL-007, BR-EL-008)"
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Under BR-EL-007, all unused Faculty VL at year end is converted into EL at <b>2 VL : 1 EL</b> (including fractions). The converted EL is credited to the faculty EL balance and carries forward.
          </Text>

          <TextInput
            label="Faculty Fusion Username"
            placeholder="Enter username (e.g. prof_sharma)"
            value={facultyUsername}
            onChange={(e) => setFacultyUsername(e.target.value)}
            required
          />

          <NumberInput
            label="Year"
            value={conversionYear}
            onChange={(val) => setConversionYear(Number(val) || new Date().getFullYear())}
            required
          />

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConversionModalOpen(false)}>
              Cancel
            </Button>
            <Button color="violet" onClick={handleConvertVl} loading={converting}>
              Execute Conversion
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}