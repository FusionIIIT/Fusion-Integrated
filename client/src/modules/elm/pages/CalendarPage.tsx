import { Container } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function CalendarPage() {
  return (
    <Container size="lg">
      <PageHeader title="Holiday Calendar" subtitle="Publish holidays and vacation periods" />
    </Container>
  );
}
