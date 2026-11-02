import { Card, Container, Group, SimpleGrid, Text, ThemeIcon, UnstyledButton } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { FaArchive, FaBook, FaClone, FaHdd, FaLayerGroup, FaUserAlt, FaClipboardCheck, FaShieldAlt } from "react-icons/fa";
import PageHeader from "../../components/PageHeader/PageHeader";

const CARDS = [
  { label: "User Directory", desc: "Search students, faculty and staff.", icon: FaBook, to: "/UserDirectory", color: "blue" },
  { label: "Upcoming Batches", desc: "Admit and manage UG, PG and PhD batches.", icon: FaLayerGroup, to: "/UpcomingBatches", color: "indigo" },
  { label: "User Management", desc: "Add faculty and staff, reset passwords.", icon: FaUserAlt, to: "/UserManagement/CreateFaculty", color: "teal" },
  { label: "Role Management", desc: "Create roles and manage module access.", icon: FaClone, to: "/RoleManagement/ManageRoleAccess", color: "grape" },
  { label: "Archive Management", desc: "Archive students and faculty records.", icon: FaArchive, to: "/archive/students", color: "orange" },
  { label: "Backup Management", desc: "Backups, restores and schedules.", icon: FaHdd, to: "/backups", color: "red" },
  { label: "BADMS Requests", desc: "Submit archival and restoration requests.", icon: FaArchive, to: "/badms/archive-requests", color: "orange" },
  { label: "Approvals & Audit", desc: "Review requests and security activity.", icon: FaClipboardCheck, to: "/badms/approvals", color: "grape" },
  { label: "Security & Encryption", desc: "Review encryption posture and audit logs.", icon: FaShieldAlt, to: "/badms/security-audit", color: "teal" },
];

const DashboardPage = () => {
  const navigate = useNavigate();

  return (
    <Container size="xl">
      <PageHeader title="Dashboard" subtitle="Fusion System Administrator — PDPM IIITDM Jabalpur" />
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
        {CARDS.map((card) => (
          <UnstyledButton key={card.label} onClick={() => navigate(card.to)}>
            <Card padding="lg" h="100%">
              <Group align="flex-start" wrap="nowrap">
                <ThemeIcon size={46} radius="md" variant="light" color={card.color}>
                  <card.icon size={20} />
                </ThemeIcon>
                <div>
                  <Text fw={600}>{card.label}</Text>
                  <Text size="sm" c="dimmed">
                    {card.desc}
                  </Text>
                </div>
              </Group>
            </Card>
          </UnstyledButton>
        ))}
      </SimpleGrid>
    </Container>
  );
};

export default DashboardPage;
