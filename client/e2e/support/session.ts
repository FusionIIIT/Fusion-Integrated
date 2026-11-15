import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { AccountKey } from "../accounts";

export const AUTH_DIR = resolve(fileURLToPath(new URL(".", import.meta.url)), "../.auth");
export const LOGIN_TRIES = 4;
export const LOGIN_RETRY_MS = 20_000;

export function stateFile(key: AccountKey): string {
  return resolve(AUTH_DIR, `${key}.json`);
}
