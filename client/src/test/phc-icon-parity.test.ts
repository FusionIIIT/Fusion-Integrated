import * as PhosphorIcons from "@phosphor-icons/react";
import { describe, expect, it } from "vitest";

export const PHC_NAV_ICONS = [
  "Stethoscope", "Calendar", "FileText", "CurrencyDollar", "Megaphone",
  "Gear", "UserCheck", "Users", "Package", "ShoppingCart", "Ambulance",
  "Broadcast", "ChartBar", "CheckCircle", "CreditCard", "Gavel",
] as const;

const EXPORTS = new Set(Object.keys(PhosphorIcons));

describe("PHC nav icon parity", () => {
  it("uses Phosphor exports for every PHC nav icon", () => {
    for (const icon of PHC_NAV_ICONS) {
      expect(EXPORTS.has(icon), `${icon} is not a Phosphor icon`).toBe(true);
    }
  });

  it("replaces the invalid FileDollarSign name", () => {
    expect(EXPORTS.has("FileDollarSign")).toBe(false);
    expect(EXPORTS.has("CurrencyDollar")).toBe(true);
  });
});
