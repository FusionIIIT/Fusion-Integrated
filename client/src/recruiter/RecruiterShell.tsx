import { Alert, Badge, Container, Text } from "@mantine/core";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { FaExclamationTriangle } from "react-icons/fa";

import { AppShellLayout, type NavGroup } from "../ui/layout/AppShellLayout";
import { useRecruiterAuth } from "./RecruiterAuth";

/** The portal's navigation is STATIC, unlike the institute shell's.
 *
 *  There is nothing to filter: a recruiter's reach is fixed by construction —
 *  their own company's postings, their own applicants, their own rounds. They
 *  hold no permissions at all, so there is no server-driven sidebar to build.
 */
const NAV: NavGroup[] = [
  {
    section: "Recruitment",
    items: [
      {
        code: "recruiter",
        label: "Recruitment",
        icon: "FaBriefcase",
        links: [
          { code: "r.postings", label: "My Postings", icon: "FaClipboardList",
            to: "/recruiter/postings" },
          { code: "r.applicants", label: "Applicants", icon: "FaUsers",
            to: "/recruiter/applicants" },
          { code: "r.interviews", label: "Interviews", icon: "FaCalendarAlt",
            to: "/recruiter/interviews" },
        ],
      },
    ],
  },
];

export function RecruiterShell() {
  const { session, logout } = useRecruiterAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const notApproved = session?.company.approval_status !== "approved";

  return (
    <AppShellLayout
      navGroups={NAV}
      activePath={pathname}
      onNavigate={(to) => navigate(to)}
      // The subtitle is the one place a recruiter always sees which company
      // they are acting for. With one account per company that is not strictly
      // ambiguous, but it makes a mis-issued invitation obvious immediately.
      brandSubtitle={`RECRUITER · ${(session?.company.name ?? "").toUpperCase()}`}
      user={{
        name: session?.full_name || session?.email || "Recruiter",
        roleLabel: session?.company.name ?? "Recruiter",
      }}
      onLogout={logout}
    >
      {notApproved && (
        <Container size="xl" pt="md">
          <Alert
            color="orange" variant="light" icon={<FaExclamationTriangle />}
            title="Your company is not currently approved"
          >
            <Text size="sm">
              Posting roles and reviewing applicants are disabled until the
              placement office approves your organisation.
            </Text>
          </Alert>
        </Container>
      )}
      <Outlet />
    </AppShellLayout>
  );
}

export function RecruiterNotFound() {
  return (
    <Container size="md" py="xl">
      <Badge variant="light" color="grape" mb="sm">Recruiter portal</Badge>
      <Text fw={700} size="lg">That page does not exist here</Text>
      <Text c="dimmed" size="sm" mt={4}>
        The recruiter portal covers your postings, your applicants and your
        interview rounds.
      </Text>
    </Container>
  );
}
