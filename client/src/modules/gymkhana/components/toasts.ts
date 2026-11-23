import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";

export function done(title: string, message: string) {
  notifications.show({ color: "green", title, message });
}

/** The server's refusal, shown as it was sent. */
export function refused(title: string, error: unknown) {
  notifications.show({ color: "red", title, message: errorMessage(error) });
}
