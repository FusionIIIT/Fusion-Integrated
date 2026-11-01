import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { MantineProvider } from "@mantine/core";
import "@mantine/core/styles.css";

import { theme } from "./theme.js";
import { AuthProvider } from "./context/AuthContext.jsx";
import RequireAuth from "./components/RequireAuth/RequireAuth.jsx";
import AppLayout from "./components/AppLayout/AppLayout.jsx";

import DashboardPage from "./pages/Dashboard/DashboardPage.jsx";
import ArchiveStudentsPage from "./pages/ArchivingPages/ArchiveStudentsPage.jsx";
import ArchiveFacultyPage from "./pages/ArchivingPages/ArchiveFacultyPage.jsx";

import DeleteUserPage from "./pages/UserManagementPages/DeleteUserPage.jsx";
import ResetUserPasswordPage from "./pages/UserManagementPages/ResetUserPasswordPage.jsx";
import FacultyCreationPage from "./pages/UserManagementPages/FacultyCreationPage.jsx";
import StaffCreationPage from "./pages/UserManagementPages/StaffCreationPage.jsx";

import CreateCustomRolePage from "./pages/RoleManagementPages/CreateCustomRolePage.jsx";
import EditUserRolePage from "./pages/RoleManagementPages/EditUserRolePage.jsx";
import ManageRoleAccessPage from "./pages/RoleManagementPages/ManageRoleAccessPage.jsx";

import UserDirectory from "./pages/UserDirectory/UserDirectory.jsx";
import UpcomingBatchesPage from "./pages/UpcomingBatches/UpcomingBatchesPage.jsx";

import BackupPage from "./pages/BackupPage/BackupPage.jsx";
import SchedulePage from "./pages/BackupPage/SchedulePage/SchedulePage.jsx";
import LoginPage from "./pages/Login/LoginPage.jsx";
import { ArchiveRequestsPage, RestoreRequestsPage, ApprovalQueuePage, StorageRequestsPage, SecurityAuditPage } from "./pages/BADMS/BADMSPages.jsx";
import { Notifications } from "@mantine/notifications";

function Layout() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/UserDirectory" element={<UserDirectory />} />
        <Route path="/UpcomingBatches" element={<UpcomingBatchesPage />} />
        <Route path="/UserManagement/CreateFaculty" element={<FacultyCreationPage />} />
        <Route path="/UserManagement/CreateStaff" element={<StaffCreationPage />} />
        <Route path="/UserManagement/DeleteUser" element={<DeleteUserPage />} />
        <Route path="/UserManagement/ResetUserPassword" element={<ResetUserPasswordPage />} />
        <Route path="/RoleManagement/CreateCustomRole" element={<CreateCustomRolePage />} />
        <Route path="/RoleManagement/EditUserRole" element={<EditUserRolePage />} />
        <Route path="/RoleManagement/ManageRoleAccess" element={<ManageRoleAccessPage />} />
        <Route path="/archive/students" element={<ArchiveStudentsPage />} />
        <Route path="/archive/faculty" element={<ArchiveFacultyPage />} />
        <Route path="/backups" element={<BackupPage />} />
        <Route path="/backups/schedules" element={<SchedulePage />} />
        <Route path="/badms/archive-requests" element={<ArchiveRequestsPage />} />
        <Route path="/badms/restore-requests" element={<RestoreRequestsPage />} />
        <Route path="/badms/approvals" element={<ApprovalQueuePage />} />
        <Route path="/badms/storage" element={<StorageRequestsPage />} />
        <Route path="/badms/security-audit" element={<SecurityAuditPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppLayout>
  );
}

function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications />
      <AuthProvider>
        <Router basename={import.meta.env.BASE_URL.replace(/\/+$/, "") || undefined}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              }
            />
          </Routes>
        </Router>
      </AuthProvider>
    </MantineProvider>
  );
}

export default App;
