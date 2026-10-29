import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { FaCalendarAlt, FaCheck, FaPlus, FaTimes } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";

interface LeaveApplication {
  id: number;
  user_id: number;
  category: string;
  category_display: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
  status_display: string;
  remarks?: string;
  created_at: string;
}

export default function LeaveApplicationsPage() {
  const { session, can } = useAuth();
  const canManage = can("elm.leave_application.manage");
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Leave Applications"
        description="View and manage employee leave requests"
        action={
          <Button
            leftSection={<FaPlus />}
            onClick={() => setIsApplyModalOpen(true)}
          >
            Apply for Leave
          </Button>
        }
      />

      <Stack gap="md" mt="md">
        <Card withBorder padding="md" radius="md">
          <Group justify="space-between" mb="sm">
            <Title order={4}>Applications Overview</Title>
            <Badge color="blue" variant="light">
              {canManage ? "HR / Manager View" : "Employee View"}
            </Badge>
          </Group>
          <Text size="sm" c="dimmed">
            {canManage
              ? "All institute leave applications awaiting review or recorded historically."
              : "Your submitted leave applications and current review statuses."}
          </Text>
        </Card>
      </Stack>
    </Container>
  );
}
