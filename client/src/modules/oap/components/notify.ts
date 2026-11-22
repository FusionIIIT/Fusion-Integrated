import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";

export function notifyError(error: unknown) {
  notifications.show({ color: "red", message: errorMessage(error) });
}

export function notifyDone(message: string) {
  notifications.show({ color: "green", message });
}
