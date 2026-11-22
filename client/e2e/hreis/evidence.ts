import { appendFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIResponse, Page, TestInfo } from "@playwright/test";

export interface WalkRequest { role: string; username: string; method: string; path: string; status: number; at: string }
export function observeApi(response: APIResponse, role: string, username: string, rows: WalkRequest[]) {
  const date = response.headers().date;
  if (!date) throw new Error("The walkthrough response must include a server Date header.");
  rows.push({ role, username, method: "GET", path: new URL(response.url()).pathname,
    status: response.status(), at: new Date(date).toISOString() });
}
export function observe(page: Page, role: string, username: string, rows: WalkRequest[]) {
  page.on("response", (response) => {
    const url = new URL(response.url());
    const timing = response.request().timing();
    const at = new Date(timing.startTime + Math.max(0, timing.responseStart)).toISOString();
    if (url.pathname.startsWith("/api/v1/hreis/")) rows.push({ role, username,
      method: response.request().method(), path: url.pathname + url.search, status: response.status(), at });
  });
}
export function saveWalkthrough(info: TestInfo, rows: WalkRequest[]) {
  const folder = process.env.E2E_EVIDENCE_DIR;
  if (folder) appendFileSync(resolve(folder, "walkthrough.jsonl"), JSON.stringify({
    test: info.title, status: info.status, requests: rows,
  }) + "\n");
}
