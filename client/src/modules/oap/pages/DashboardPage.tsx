import React, { useState } from 'react';
import { Container, Title, Text, Tabs, Card, Badge, Group, Stack, Table } from '@mantine/core';

export const DashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string | null>('leave');

  return (
    <Container size="xl" py="lg">
      <Stack gap="md">
        <div>
          <Title order={2}>Other Academic Procedures (OAP)</Title>
          <Text c="dimmed" size="sm">
            Integrated Portal for Academic Operations, No-Dues Clearance, Leaves, and PG Assistantships
          </Text>
        </div>

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="leave">Student Leave</Tabs.Tab>
            <Tabs.Tab value="bonafide">Bonafide Certificate</Tabs.Tab>
            <Tabs.Tab value="nodues">No-Dues Clearance</Tabs.Tab>
            <Tabs.Tab value="assistantship">PG Assistantship</Tabs.Tab>
            <Tabs.Tab value="seminars">Graduate Seminars</Tabs.Tab>
            <Tabs.Tab value="assignments">Supervisors & TAs</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="leave" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Student Leave Management</Title>
              <Text size="sm" c="dimmed" mb="md">Track casual and medical leaves with HoD review status.</Text>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Type</Table.Th>
                    <Table.Th>From</Table.Th>
                    <Table.Th>To</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>#LV-101</Table.Td>
                    <Table.Td>CASUAL</Table.Td>
                    <Table.Td>2026-11-05</Table.Td>
                    <Table.Td>2026-11-07</Table.Td>
                    <Table.Td><Badge color="blue">SUBMITTED</Badge></Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="bonafide" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Bonafide Certificate Requests</Title>
              <Text size="sm" c="dimmed" mb="md">Request and verify digitally approved bonafide certificates.</Text>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Request ID</Table.Th>
                    <Table.Th>Purpose</Table.Th>
                    <Table.Th>Certificate Number</Table.Th>
                    <Table.Th>Status</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>#BN-201</Table.Td>
                    <Table.Td>Passport Application</Table.Td>
                    <Table.Td>BONAFIDE-201-20261102</Table.Td>
                    <Table.Td><Badge color="green">APPROVED</Badge></Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="nodues" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">7-Domain No-Dues Clearance Tracker</Title>
              <Text size="sm" c="dimmed" mb="md">Mandatory verification across Library, Hostel, Mess, Department, Lab, Academic & Student Sections.</Text>
              <Group gap="xs" mb="md">
                <Badge color="green" variant="light">Library: CLEARED</Badge>
                <Badge color="green" variant="light">Hostel: CLEARED</Badge>
                <Badge color="green" variant="light">Mess: CLEARED</Badge>
                <Badge color="green" variant="light">Department: CLEARED</Badge>
                <Badge color="green" variant="light">Lab: CLEARED</Badge>
                <Badge color="green" variant="light">Academic: CLEARED</Badge>
                <Badge color="green" variant="light">Student Section: CLEARED</Badge>
              </Group>
              <Badge color="teal" size="lg">CLEARANCE FINALIZED</Badge>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="assistantship" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">PG Assistantship Claims</Title>
              <Text size="sm" c="dimmed" mb="md">Dual supervisor verification (Thesis & TA) and HoD stipend approval workflow.</Text>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Claim ID</Table.Th>
                    <Table.Th>Month / Year</Table.Th>
                    <Table.Th>Dual Verification</Table.Th>
                    <Table.Th>HoD Status</Table.Th>
                    <Table.Th>Stipend</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>#AS-301</Table.Td>
                    <Table.Td>October 2026</Table.Td>
                    <Table.Td><Badge color="teal">VERIFIED (DUAL)</Badge></Table.Td>
                    <Table.Td><Badge color="green">APPROVED</Badge></Table.Td>
                    <Table.Td><Badge color="blue">DISBURSED (₹12,400)</Badge></Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="seminars" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Graduate Seminars</Title>
              <Text size="sm" c="dimmed" mb="md">Department graduate research seminars and scheduling.</Text>
              <Text size="sm">No upcoming seminars pending scheduling.</Text>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="assignments" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Supervisor & TA Allocations</Title>
              <Text size="sm" c="dimmed" mb="md">Thesis supervisor and Teaching Assistant course assignments.</Text>
              <Text size="sm">Department allocations active for Academic Year 2026-2027.</Text>
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
};

export default DashboardPage;
