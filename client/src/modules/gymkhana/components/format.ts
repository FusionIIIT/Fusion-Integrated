export function date(value: string): string {
  return new Date(value).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

export function dateTime(value: string): string {
  return new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function time(value: string): string {
  return value.slice(0, 5);
}

export function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/** The person's name, or their id while the directory has not answered. */
export function person(name: string, id: number): string {
  return name || `User ${id}`;
}
