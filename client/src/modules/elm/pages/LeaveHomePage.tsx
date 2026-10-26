import { Paper, Stack, Text, Title } from "@mantine/core";

export default function LeaveHomePage() {
  return (
    <Paper p="lg" withBorder>
      <Stack gap="sm">
        <Title order={2}>Employee Leave Management</Title>
        <Text>
          ELM module shell. Leave workflows are not implemented yet.
        </Text>
      </Stack>
    </Paper>
  );
}
