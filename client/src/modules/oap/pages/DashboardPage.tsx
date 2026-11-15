import React, { useState } from 'react';
import { Container, Title, Text, Tabs, Card, Badge, Group, Stack, Table, Button, SimpleGrid, Paper, ThemeIcon, Progress } from '@mantine/core';

export const DashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string | null>('leave');

  return (
    <Container size="xl" py="lg">
      <Stack gap="md">
        <div>
          <Title order={2}>Other Academic Procedures (OAP) — Enterprise Portal</Title>
          <Text c="dimmed" size="sm">
            Phase 2 Hardened Infrastructure: Multi-Domain Clearance, Dual-Supervisor Assistantships, and Audit Logs
          </Text>
        </div>

        {/* Quick KPI Overview */}
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Student Leave Balance</Text>
            <Title order={3} mt="xs">12.0 Days</Title>
            <Text size="xs" c="teal" mt={4}>Casual & Academic Quota Active</Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">No-Dues Clearance</Text>
            <Title order={3} mt="xs">6 / 7 Cleared</Title>
            <Progress value={(6 / 7) * 100} color="indigo" size="sm" mt="xs" />
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">PG Assistantship (Oct 2026)</Text>
            <Title order={3} mt="xs">₹12,400.00</Title>
            <Text size="xs" c="blue" mt={4}>Dual-Supervisor Verified</Text>
          </Paper>
          <Paper withBorder p="md" radius="md">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">Audit Trail Records</Text>
            <Title order={3} mt="xs">26 Events</Title>
            <Text size="xs" c="gray" mt={4}>Immutable Event Hash Logged</Text>
          </Paper>
        </SimpleGrid>

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="leave">Student Leave</Tabs.Tab>
            <Tabs.Tab value="bonafide">Bonafide Certificates</Tabs.Tab>
            <Tabs.Tab value="nodues">7-Domain No-Dues</Tabs.Tab>
            <Tabs.Tab value="assistantship">PG Assistantship Claims</Tabs.Tab>
            <Tabs.Tab value="seminars">Graduate Seminars</Tabs.Tab>
            <Tabs.Tab value="assignments">Supervisors & TAs</Tabs.Tab>
            <Tabs.Tab value="audit">Audit Log</Tabs.Tab>
          </Tabs.List>

          {/* TAB 1: STUDENT LEAVE */}
          <Tabs.Panel value="leave" pt="md">
            <Card withBorder padding="md" radius="md">
              <Group justify="space-between" mb="md">
                <div>
                  <Title order={4}>Student Leave Applications</Title>
                  <Text size="sm" c="dimmed">Enforcing OA-BR-11 HoD sole authority, medical proof validation, and date rules.</Text>
                </div>
                <Button size="xs" variant="filled" color="blue">Apply for Leave</Button>
              </Group>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Application ID</Table.Th>
                    <Table.Th>Type</Table.Th>
                    <Table.Th>Dates</Table.Th>
                    <Table.Th>Days</Table.Th>
                    <Table.Th>Medical Proof</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>HoD Remarks</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>#LV-2026-001</Table.Td>
                    <Table.Td>CASUAL</Table.Td>
                    <Table.Td>2026-11-10 to 2026-11-12</Table.Td>
                    <Table.Td>3.0</Table.Td>
                    <Table.Td><Badge color="gray">N/A</Badge></Table.Td>
                    <Table.Td><Badge color="green">APPROVED</Badge></Table.Td>
                    <Table.Td>Approved by HoD CSE</Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>#LV-2026-002</Table.Td>
                    <Table.Td>MEDICAL</Table.Td>
                    <Table.Td>2026-11-15 to 2026-11-19</Table.Td>
                    <Table.Td>5.0</Table.Td>
                    <Table.Td><Badge color="teal">ATTACHED (MED-9821)</Badge></Table.Td>
                    <Table.Td><Badge color="blue">SUBMITTED</Badge></Table.Td>
                    <Table.Td>Awaiting HoD Review</Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          {/* TAB 2: BONAFIDE CERTIFICATES */}
          <Tabs.Panel value="bonafide" pt="md">
            <Card withBorder padding="md" radius="md">
              <Group justify="space-between" mb="md">
                <div>
                  <Title order={4}>Bonafide Certificate Requests</Title>
                  <Text size="sm" c="dimmed">Digitally signed certificates with cryptographic verification tokens (OA-BR-21, 22).</Text>
                </div>
                <Button size="xs" variant="filled" color="indigo">Request Bonafide</Button>
              </Group>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Certificate No.</Table.Th>
                    <Table.Th>Purpose</Table.Th>
                    <Table.Th>Issue Date</Table.Th>
                    <Table.Th>Valid Until</Table.Th>
                    <Table.Th>Verification Hash</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Action</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>BONAFIDE-102-20261102</Table.Td>
                    <Table.Td>Passport Verification</Table.Td>
                    <Table.Td>2026-11-02</Table.Td>
                    <Table.Td>2027-05-01</Table.Td>
                    <Table.Td><code style={{ fontSize: '11px' }}>c8f41e0a29b7d34a</code></Table.Td>
                    <Table.Td><Badge color="green">APPROVED</Badge></Table.Td>
                    <Table.Td><Button size="compact-xs" variant="light" color="blue">Download PDF</Button></Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          {/* TAB 3: 7-DOMAIN NO-DUES CLEARANCE */}
          <Tabs.Panel value="nodues" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Multi-Domain Parallel Clearance (OA-BR-31..34)</Title>
              <Text size="sm" c="dimmed" mb="md">
                Mandatory clearance across all 7 institutional authorities before Academic Admin final sign-off.
              </Text>
              <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="xs" mb="lg">
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>1. Library</Text>
                  <Badge color="green" size="sm" mt={4}>CLEARED</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>2. Hostel Warden</Text>
                  <Badge color="green" size="sm" mt={4}>CLEARED</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>3. Mess In-Charge</Text>
                  <Badge color="green" size="sm" mt={4}>CLEARED</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>4. Dept Administrator</Text>
                  <Badge color="green" size="sm" mt={4}>CLEARED</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>5. Laboratory</Text>
                  <Badge color="green" size="sm" mt={4}>CLEARED</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>6. Academic Section</Text>
                  <Badge color="green" size="sm" mt={4}>CLEARED</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm">
                  <Text size="xs" fw={600}>7. Student Section</Text>
                  <Badge color="yellow" size="sm" mt={4}>PENDING DUES</Badge>
                </Paper>
                <Paper withBorder p="xs" radius="sm" style={{ background: '#f8fafc' }}>
                  <Text size="xs" fw={600}>Consolidated State</Text>
                  <Badge color="orange" size="sm" mt={4}>DUES PENDING</Badge>
                </Paper>
              </SimpleGrid>
              <Button disabled variant="outline" color="gray" size="xs">
                Finalize & Release Certificate (Blocked until Domain 7 Clears)
              </Button>
            </Card>
          </Tabs.Panel>

          {/* TAB 4: PG ASSISTANTSHIP CLAIMS */}
          <Tabs.Panel value="assistantship" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">PG Teaching & Research Assistantship (OA-BR-41..46)</Title>
              <Text size="sm" c="dimmed" mb="md">
                Dual supervisor verification (Thesis Guide + Course TA), pro-rata calculation, and HoD approval.
              </Text>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Month/Year</Table.Th>
                    <Table.Th>Hours</Table.Th>
                    <Table.Th>Attendance</Table.Th>
                    <Table.Th>Thesis Guide</Table.Th>
                    <Table.Th>TA Guide</Table.Th>
                    <Table.Th>Dept Review</Table.Th>
                    <Table.Th>HoD Sanction</Table.Th>
                    <Table.Th>Disbursed Stipend</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>10/2026</Table.Td>
                    <Table.Td>40.0 hrs</Table.Td>
                    <Table.Td><Badge color="teal">100%</Badge></Table.Td>
                    <Table.Td><Badge color="green">VERIFIED</Badge></Table.Td>
                    <Table.Td><Badge color="green">VERIFIED</Badge></Table.Td>
                    <Table.Td><Badge color="green">REVIEWED</Badge></Table.Td>
                    <Table.Td><Badge color="green">APPROVED</Badge></Table.Td>
                    <Table.Td fw={700}>₹12,400.00 (Disbursed)</Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>11/2026</Table.Td>
                    <Table.Td>20.0 hrs</Table.Td>
                    <Table.Td><Badge color="orange">60% (Pro-Rata)</Badge></Table.Td>
                    <Table.Td><Badge color="green">VERIFIED</Badge></Table.Td>
                    <Table.Td><Badge color="blue">AWAITING</Badge></Table.Td>
                    <Table.Td><Badge color="gray">PENDING</Badge></Table.Td>
                    <Table.Td><Badge color="gray">PENDING</Badge></Table.Td>
                    <Table.Td fw={700}>₹7,440.00 (Calculated)</Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          {/* TAB 5: GRADUATE SEMINARS */}
          <Tabs.Panel value="seminars" pt="md">
            <Card withBorder padding="md" radius="md">
              <Group justify="space-between" mb="md">
                <div>
                  <Title order={4}>Graduate Research Seminars (OA-BR-61..63)</Title>
                  <Text size="sm" c="dimmed">PG seminar requests, collision-free hall scheduling, and evaluation rubrics.</Text>
                </div>
                <Button size="xs" variant="filled" color="cyan">Submit Seminar Request</Button>
              </Group>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Seminar Topic</Table.Th>
                    <Table.Th>Proposed Date</Table.Th>
                    <Table.Th>Scheduled Hall</Table.Th>
                    <Table.Th>Time Slot</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Evaluation</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>Consensus Protocols in Distributed ERP</Table.Td>
                    <Table.Td>2026-11-20</Table.Td>
                    <Table.Td>Seminar Hall A</Table.Td>
                    <Table.Td>15:00 - 16:30</Table.Td>
                    <Table.Td><Badge color="green">COMPLETED</Badge></Table.Td>
                    <Table.Td><Badge color="teal">SATISFACTORY</Badge></Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          {/* TAB 6: SUPERVISOR & TA ASSIGNMENTS */}
          <Tabs.Panel value="assignments" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Academic Supervision & TA Allocation (OA-BR-51, 52)</Title>
              <Text size="sm" c="dimmed" mb="md">Department Administrator recorded thesis guides and course TA associations.</Text>
              <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                <Paper withBorder p="md" radius="md">
                  <Text size="sm" fw={700} c="blue">Active Thesis Supervisor</Text>
                  <Text size="md" mt={4}>Prof. P. Sharma (CSE Dept)</Text>
                  <Text size="xs" c="dimmed">Academic Year: 2026-2027 • Active Guide</Text>
                </Paper>
                <Paper withBorder p="md" radius="md">
                  <Text size="sm" fw={700} c="indigo">Course TA Assignment</Text>
                  <Text size="md" mt={4}>CS301 — Operating Systems Lab</Text>
                  <Text size="xs" c="dimmed">Semester: Autumn 2026 • Lead Faculty: Dr. R. Verma</Text>
                </Paper>
              </SimpleGrid>
            </Card>
          </Tabs.Panel>

          {/* TAB 7: AUDIT TRAIL */}
          <Tabs.Panel value="audit" pt="md">
            <Card withBorder padding="md" radius="md">
              <Title order={4} mb="xs">Immutable Security Audit Trail</Title>
              <Text size="sm" c="dimmed" mb="md">Real-time ledger recording actor identities, roles, state changes, and event hashes.</Text>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Timestamp</Table.Th>
                    <Table.Th>Procedure</Table.Th>
                    <Table.Th>Action</Table.Th>
                    <Table.Th>Actor Role</Table.Th>
                    <Table.Th>Transition</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>2026-11-02 09:27:14</Table.Td>
                    <Table.Td>LEAVE</Table.Td>
                    <Table.Td>HOD_APPROVED</Table.Td>
                    <Table.Td><Badge color="indigo" size="xs">HOD</Badge></Table.Td>
                    <Table.Td>SUBMITTED &rarr; <Badge color="green" size="xs">APPROVED</Badge></Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>2026-11-02 09:27:08</Table.Td>
                    <Table.Td>NODUES</Table.Td>
                    <Table.Td>FINALIZE_NODUES</Table.Td>
                    <Table.Td><Badge color="blue" size="xs">Academic Admin</Badge></Table.Td>
                    <Table.Td>VERIFICATION_COMPLETE &rarr; <Badge color="green" size="xs">FINALIZED</Badge></Table.Td>
                  </Table.Tr>
                  <Table.Tr>
                    <Table.Td>2026-11-02 09:26:55</Table.Td>
                    <Table.Td>ASSISTANTSHIP</Table.Td>
                    <Table.Td>DISBURSE_STIPEND</Table.Td>
                    <Table.Td><Badge color="blue" size="xs">Academic Admin</Badge></Table.Td>
                    <Table.Td>APPROVED &rarr; <Badge color="teal" size="xs">STIPEND_PROCESSED</Badge></Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
};
