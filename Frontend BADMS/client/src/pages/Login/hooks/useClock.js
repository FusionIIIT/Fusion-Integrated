import { useEffect, useState } from "react";

const formatDate = () =>
  new Date()
    .toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
    .toUpperCase();

/**
 * Returns the current date as a display string (e.g. "12 JUL 2026"), refreshed once
 * a minute. We only show the date, so a per-minute tick is plenty — no per-second
 * timer burning renders in the background.
 */
export function useClock() {
  const [date, setDate] = useState(formatDate);

  useEffect(() => {
    const id = setInterval(() => setDate(formatDate()), 60_000);
    return () => clearInterval(id);
  }, []);

  return date;
}
