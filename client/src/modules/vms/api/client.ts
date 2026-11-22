import { VisitRequest, VisitorPass, VisitLog, Gate } from "./types";

const BASE_URL = "/api/v1/vms";

export async function preRegisterVisit(payload: any): Promise<VisitRequest> {
  const res = await fetch(`${BASE_URL}/requests/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Failed to submit pre-registration");
  }
  return res.json();
}

export async function fetchHostPending(): Promise<VisitRequest[]> {
  const res = await fetch(`${BASE_URL}/host/pending/`);
  if (!res.ok) throw new Error("Failed to load pending requests");
  return res.json();
}

export async function decideVisitRequest(requestId: string, payload: { outcome: "APPROVE" | "REJECT"; special_instructions?: string }): Promise<any> {
  const res = await fetch(`${BASE_URL}/requests/${requestId}/decision/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to record decision");
  return res.json();
}

export async function validateGateEntry(payload: { credential_data: string; gate_id: string; verifier_notes?: string }) {
  const res = await fetch(`${BASE_URL}/gate/validate/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function checkoutGateExit(payload: { pass_id: string; gate_id: string; verifier_notes?: string }) {
  const res = await fetch(`${BASE_URL}/gate/checkout/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error || "Failed to process checkout");
  }
  return res.json();
}

export async function fetchActivePasses(): Promise<VisitorPass[]> {
  const res = await fetch(`${BASE_URL}/passes/active/`);
  return res.json();
}

export async function fetchActiveVisits(): Promise<VisitLog[]> {
  const res = await fetch(`${BASE_URL}/visits/active/`);
  return res.json();
}

export async function fetchGates(): Promise<Gate[]> {
  const res = await fetch(`${BASE_URL}/gates/`);
  return res.json();
}
