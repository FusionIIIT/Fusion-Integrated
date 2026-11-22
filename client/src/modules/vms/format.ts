import dayjs from "dayjs";

/** "5 Jan, 09:30" — the campus clock, in the browser's zone. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = dayjs(value);
  return d.isValid() ? d.format("D MMM, HH:mm") : "—";
}

/** "5 Jan, 09:30 – 11:00", or both ends in full when the visit spans midnight. */
export function formatWindow(start: string, end: string): string {
  const a = dayjs(start);
  const b = dayjs(end);
  if (!a.isValid() || !b.isValid()) return "—";
  return a.isSame(b, "day")
    ? `${a.format("D MMM, HH:mm")} – ${b.format("HH:mm")}`
    : `${a.format("D MMM, HH:mm")} – ${b.format("D MMM, HH:mm")}`;
}

/** "gate_failure" → "Gate failure". */
export function humanise(code: string): string {
  const text = code.replace(/[_.]+/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
}
