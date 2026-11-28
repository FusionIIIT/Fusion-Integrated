import { Alert, Loader, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { http } from "../../../lib/http";

export default function LeavePage() {
  const catalog = useQuery({ queryKey: ["elm", "catalog"], queryFn: async () =>
    (await http.get<{ entitlements: Record<string, string> }>("/elm/catalog")).data });
  if (catalog.isLoading) return <Loader />;
  if (catalog.isError) return <Alert color="red">Leave data is unavailable.</Alert>;
  return <Stack><Title order={2}>Employee Leave Management</Title>
    <Text>Your annual configured leave entitlements are shown below.</Text>
    {Object.entries(catalog.data.entitlements).map(([category, days]) =>
      <Text key={category}>{category}: {days} days</Text>)}</Stack>;
}
