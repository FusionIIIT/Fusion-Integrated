import { Alert, Text } from "@mantine/core";
import { FaLock } from "react-icons/fa";

/** A page the acting role may not use: said plainly, with nothing on it to press. */
export function NotPermitted() {
  return (
    <Alert color="gray" variant="light" icon={<FaLock />} title="Not available to your role">
      <Text size="sm">
        This page is for another role. If you hold that role, switch to it from the sidebar.
      </Text>
    </Alert>
  );
}
