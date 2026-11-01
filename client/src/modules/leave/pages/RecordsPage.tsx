import { useState } from "react";
import { Card, Container, Group, SimpleGrid, Text, TextInput } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { AdminForm } from "../components/AdminForm";

const CATS = ["CL", "RH", "SCL", "EL", "COL", "VL"];

/** EL-UC-016/017: synchronising records, never a second sanction (BR-EL-037). */
export default function RecordsPage() {
  const [userId, setUserId] = useState("");
  const year = new Date().getFullYear();
  const lookup = useQuery({
    queryKey: ["leave", "employee-balances", userId, year],
    enabled: /^\d+$/.test(userId),
    queryFn: async () => (await http.get<{ balances: Record<string, string> }>(
      `/leave/records/${userId}/balances`, { params: { year } })).data.balances,
  });

  return (
    <Container size="lg">
      <PageHeader title="Leave Records"
        subtitle="Offline-sanctioned leave and balance corrections" />
      <AdminForm title="Record leave already sanctioned offline" path="/leave/records/offline"
        fields={[{ name: "user_id", label: "Employee user id", type: "number" },
          { name: "category", label: "Category", type: "select", options: CATS },
          { name: "start_date", label: "From", type: "date" },
          { name: "end_date", label: "To", type: "date" },
          { name: "reference", label: "Sanction order / reference" },
          { name: "purpose", label: "Purpose", optional: true }]} />
      <AdminForm title="Correct a balance (reversing entry)" path="/leave/records/corrections"
        fields={[{ name: "user_id", label: "Employee user id", type: "number" },
          { name: "category", label: "Category", type: "select", options: CATS },
          { name: "year", label: "Year", type: "number" },
          { name: "days", label: "Days (+/-)" },
          { name: "note", label: "Reason" }]} />
      <Card withBorder>
        <Group align="flex-end">
          <TextInput label={`Balances in ${year} for user id`} value={userId}
            onChange={(e) => setUserId(e.currentTarget.value.trim())} />
        </Group>
        {lookup.error && <ErrorState error={lookup.error} />}
        {lookup.data && (
          <SimpleGrid cols={{ base: 3, sm: 6 }} mt="md">
            {Object.entries(lookup.data).map(([cat, days]) => (
              <div key={cat}><Text size="xs" c="dimmed">{cat}</Text>
                <Text fw={700}>{Number(days)}</Text></div>))}
          </SimpleGrid>
        )}
      </Card>
    </Container>
  );
}
