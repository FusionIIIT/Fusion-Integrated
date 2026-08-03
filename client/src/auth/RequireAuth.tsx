import { Alert, Center, Loader, Stack, Text } from "@mantine/core";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return <Center h="100vh"><Loader /></Center>;
  }
  // Not a logout: signing in again cannot work while the IAM is unreachable.
  if (status === "unavailable") {
    return (
      <Center h="100vh" p="md">
        <Alert color="red" title="Cannot verify your session" maw={460}>
          <Stack gap={4}>
            <Text size="sm">
              The identity service could not be reached, so it is not known
              whether you are signed in. You have not been signed out.
            </Text>
            <Text size="sm" c="dimmed">Reload once it is back.</Text>
          </Stack>
        </Alert>
      </Center>
    );
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ next: location.pathname }} />;
  }
  return <>{children}</>;
}
