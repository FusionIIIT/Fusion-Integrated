// Display helpers shared by the PMS pages.

export function words(value: string | null | undefined): string {
  if (!value) return "—";
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function day(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 10);
}

export function money(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  return `Rs ${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

export const ROLE_NAMES: Record<string, string> = {
  pms_director: "Director", pms_pcc_admin: "PCC_ADMIN", pms_attorney: "Attorney",
};

export const SENSITIVITY_NAMES: Record<string, string> = {
  public_internal: "Public-internal", confidential: "Confidential", restricted: "Restricted",
};
