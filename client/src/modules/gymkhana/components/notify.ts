import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";

export function notifyDone(title: string, message: string) {
  notifications.show({ color: "green", title, message });
}

export function notifyFailed(title: string, error: unknown) {
  notifications.show({ color: "red", title, message: errorMessage(error) });
}
