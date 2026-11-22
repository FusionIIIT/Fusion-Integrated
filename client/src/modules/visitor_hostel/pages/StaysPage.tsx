import { Alert, Title } from "@mantine/core";

export default function StaysPage() {
  return (
    <>
      <Title order={2}>Rooms and stays</Title>
      <Alert mt="md" title="Operational view">
        Use the Caretaker booking queue and the checkout actions from a booking detail.
      </Alert>
    </>
  );
}
