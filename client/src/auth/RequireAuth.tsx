import { Center, Loader } from "@mantine/core";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <Center h="100vh"><Loader /></Center>;
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ next: location.pathname }} />;
  }
  return <>{children}</>;
}
