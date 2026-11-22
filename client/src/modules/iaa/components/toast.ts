import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";

export function done(message: string) {
  notifications.show({ color: "green", message });
}

export function failed(e: unknown) {
  notifications.show({ color: "red", title: "Not done", message: errorMessage(e) });
}
