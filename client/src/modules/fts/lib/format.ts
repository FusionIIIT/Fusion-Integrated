import dayjs from "dayjs";

export function formatTime(value: string | null | undefined): string {
  if (!value) return "-";
  const d = dayjs(value);
  return d.isValid() ? d.format("DD MMM YYYY, HH:mm") : "-";
}
