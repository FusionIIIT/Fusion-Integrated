/** FTS views answer {"error": "<message>"} for a rejected action, DRF answers
 *  {"field": ["message"]} for a bad payload, and the platform wraps other
 *  failures as {"error": {"message", "details"}}. The shared errorMessage only
 *  knows the last one, so FTS reads all three. */
export function ftsErrorMessage(e: unknown): string {
  const data = (e as { response?: { data?: unknown } })?.response?.data;
  if (typeof data === "string" && data.trim() && !data.includes("<")) return data;
  if (!data || typeof data !== "object") {
    return "Something went wrong. Please try again.";
  }
  const body = data as Record<string, unknown>;

  const err = body.error;
  if (typeof err === "string" && err) return err;
  if (err && typeof err === "object") {
    const env = err as {
      message?: string; details?: { field?: string; message?: string }[];
    };
    const details = env.details
      ?.filter((d) => d.message)
      .map((d) => (d.field ? `${d.field}: ${d.message}` : d.message))
      .join(" ");
    return details || env.message || "Request failed.";
  }
  if (typeof body.detail === "string") return body.detail;

  const parts: string[] = [];
  for (const [field, value] of Object.entries(body)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    parts.push(`${field}: ${text}`);
  }
  return parts.join(" ") || "Request failed.";
}
