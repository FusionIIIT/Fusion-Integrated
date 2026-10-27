import { Grid, Stack, Title } from "@mantine/core";
import { useState } from "react";
import LeaveHistory from "../components/LeaveHistory";
import LeaveRequestForm from "../components/LeaveRequestForm";

export default function LeavePage() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <Stack gap="lg" p="md">
      <Title order={2}>Employee Leave Management</Title>
      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 5 }}>
          <LeaveRequestForm onSuccess={handleSuccess} />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 7 }}>
          <LeaveHistory refreshKey={refreshKey} />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
