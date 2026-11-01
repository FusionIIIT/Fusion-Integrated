import { useEffect, useState } from "react";
import { Badge, Card, Container, Grid, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { mmsApi } from "../api";
import type { DailyMenuItem, MessRoleAssignment, RegistrationWindow } from "../types";

export default function DashboardPage() {
  const [activeRoles, setActiveRoles] = useState<{
    caretaker: MessRoleAssignment | null;
    warden: MessRoleAssignment | null;
  }>({ caretaker: null, warden: null });
  const [window, setWindow] = useState<RegistrationWindow | null>(null);
  const [menu, setMenu] = useState<DailyMenuItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [rolesData, menuData] = await Promise.all([
          mmsApi.getActiveRoles(),
          mmsApi.getWeeklyMenu(),
        ]);
        setActiveRoles(rolesData);
        setMenu(menuData);
        try {
          const winData = await mmsApi.getCurrentWindow();
          setWindow(winData);
        } catch {
          // Window may not be open
        }
      } catch (err) {
        console.error("Failed to load MMS dashboard data", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center"><Loader size="lg" /></Group>
      </Container>
    );
  }

  return (
    <Container size="lg" py="md">
      <Stack gap="lg">
        <div>
          <Title order={2}>Mess Management System (MMS)</Title>
          <Text c="dimmed">Operational mess management, meal schedules, registrations, and rebates.</Text>
        </div>

        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Active Administration</Title>
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text fw={500}>Mess Caretaker:</Text>
                  {activeRoles.caretaker ? (
                    <Badge color="blue">Employee #{activeRoles.caretaker.employee_id}</Badge>
                  ) : (
                    <Badge color="gray">Not Assigned</Badge>
                  )}
                </Group>
                <Group justify="space-between">
                  <Text fw={500}>Mess Warden:</Text>
                  {activeRoles.warden ? (
                    <Badge color="violet">Employee #{activeRoles.warden.employee_id}</Badge>
                  ) : (
                    <Badge color="gray">Not Assigned</Badge>
                  )}
                </Group>
              </Stack>
            </Card>
          </Grid.Col>

          <Grid.Col span={{ base: 12, md: 6 }}>
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Registration Window</Title>
              {window && window.is_open ? (
                <Stack gap="xs">
                  <Text fw={500}>{window.name}</Text>
                  <Text size="sm">Valid: {window.start_date} to {window.end_date}</Text>
                  <Badge color="green">Open for Applications</Badge>
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">No registration window is currently open.</Text>
              )}
            </Card>
          </Grid.Col>
        </Grid>

        <Card withBorder padding="md" radius="md">
          <Title order={4} mb="sm">Weekly Menu Overview</Title>
          {menu.length === 0 ? (
            <Text c="dimmed" size="sm">No published menu items available.</Text>
          ) : (
            <Grid>
              {menu.slice(0, 6).map((item) => (
                <Grid.Col key={item.id} span={{ base: 12, sm: 6, md: 4 }}>
                  <Card withBorder shadow="none" padding="xs" radius="sm">
                    <Group justify="space-between" mb="xs">
                      <Text fw={600} size="sm">{item.day_of_week}</Text>
                      <Badge size="xs" variant="light">{item.meal_time}</Badge>
                    </Group>
                    <Text size="xs" lineClamp={2}>{item.items}</Text>
                  </Card>
                </Grid.Col>
              ))}
            </Grid>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
