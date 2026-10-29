import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Group, Title, Textarea, LoadingOverlay, Alert, Container, Paper, Table } from "@mantine/core";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { getConfiguration, saveConfiguration, getRecords, type Configuration } from "../api";

const LeaveAdminPage = () => {
  const [policyJSON, setPolicyJSON] = useState('');
  const [calendarJSON, setCalendarJSON] = useState('');

  // Fetch configuration data initially
  const { isLoading, isError, error, data } = useQuery({ queryKey: ['configuration'], queryFn: async () => {
    return await getConfiguration();
  } });

  useEffect(() => {
    if (data) {
      setPolicyJSON(JSON.stringify(data.policy || [], null, 2));
      setCalendarJSON(JSON.stringify(data.calendar || [], null, 2));
    }
  }, [data]);

  const saveConfigurationMutation = useMutation({
    mutationFn: async (newData: Configuration) => {
      return await saveConfiguration(newData);
    },
    onSuccess: () => {
      alert('Configuration saved successfully!');
    },
    onError: (error) => {
      console.error(error);
      alert('Failed to save configuration.');
    },
  });

  const handleSavePolicyClick = () => {
    try {
      const parsedPolicy = JSON.parse(policyJSON);
      saveConfigurationMutation.mutate({ policy: parsedPolicy });
    } catch (e) {
      alert('Invalid JSON format for policy');
    }
  };

  const handleSaveCalendarClick = () => {
    try {
      const parsedCalendar = JSON.parse(calendarJSON);
      saveConfigurationMutation.mutate({ calendar: parsedCalendar });
    } catch (e) {
      alert('Invalid JSON format for calendar');
    }
  };

  // Fetch records
  const { isLoading: isLoadingRecords, isError: isErrorRecords, data: dataRecords } = useQuery({ queryKey: ['records'], queryFn: async () => {
    return await getRecords();
  } });

  useEffect(() => {
    if (dataRecords && dataRecords.history) {
      setHistory(dataRecords.history);
    }

    if (dataRecords && dataRecords.notifications) {
      setNotifications(dataRecords.notifications);
    }
  }, [dataRecords]);

  const [history, setHistory] = useState<Record<string, any>[]>([]);
  const [notifications, setNotifications] = useState<Record<string, any>[]>([]);

  return (
    <Container size="lg" mt={40}>
      <PageHeader title="Leave Admin" subtitle="Manage leave policies and configurations." />

      {/* Policy Editor */}
      <Paper shadow="sm" p="md">
        <Title order={3}>Policy</Title>
        <Textarea value={policyJSON} onChange={(event) => setPolicyJSON(event.target.value)} rows={15} />
        <Group justify="right" mt="xs">
          <Button onClick={handleSavePolicyClick} color="blue">Save Policy</Button>
        </Group>
      </Paper>

      {/* Calendar Editor */}
      <Paper shadow="sm" p="md" mt={20}>
        <Title order={3}>Calendar</Title>
        <Textarea value={calendarJSON} onChange={(event) => setCalendarJSON(event.target.value)} rows={15} />
        <Group justify="right" mt="xs">
          <Button onClick={handleSaveCalendarClick} color="green">Save Calendar</Button>
        </Group>
      </Paper>

      {isLoading || isLoadingRecords ? (
        <LoadingOverlay visible={true} overlayProps={{ blur: 2 }} />
      ) : isError || isErrorRecords ? (
        <Alert color="red">{errorMessage(error)}</Alert>
      ) : (
        <>
          <Title order={4} mt={20}>History</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Date</Table.Th>
                <Table.Th>Details</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {history.map((record, index) => (
                <Table.Tr key={index}>
                  <Table.Td>{new Date(record.date).toLocaleDateString()}</Table.Td>
                  <Table.Td>{record.details}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>

          <Title order={4} mt={20}>Notifications</Title>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Title</Table.Th>
                <Table.Th>Description</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {notifications.map((notification, index) => (
                <Table.Tr key={index}>
                  <Table.Td>{notification.title}</Table.Td>
                  <Table.Td>{notification.description}</Table.Td>
                  <Table.Td>{notification.status}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </>
      )}
    </Container>
  );
};

export default LeaveAdminPage;
