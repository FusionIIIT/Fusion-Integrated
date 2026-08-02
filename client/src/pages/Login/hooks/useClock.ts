import { useEffect, useState } from "react";

/** "3 AUG 2026", refreshed on the minute. Matches the sysadmin header exactly. */
export function useClock(): string {
  const format = () =>
    new Date().toLocaleDateString("en-GB", {
      day: "numeric", month: "short", year: "numeric",
    }).toUpperCase();

  const [date, setDate] = useState(format);

  useEffect(() => {
    const id = setInterval(() => setDate(format()), 60_000);
    return () => clearInterval(id);
  }, []);

  return date;
}
