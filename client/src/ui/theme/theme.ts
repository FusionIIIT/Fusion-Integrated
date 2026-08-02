/** Ported verbatim from Fusion_System_Administrator/client/src/theme.js.
 *  The two apps must look like one product, so this file is a copy, not a
 *  redesign. Change it there and here together, or not at all. */
import { createTheme, type MantineThemeOverride } from "@mantine/core";

const SANS =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

export const theme: MantineThemeOverride = createTheme({
  primaryColor: "blue",
  primaryShade: { light: 6, dark: 5 },
  fontFamily: SANS,
  headings: { fontFamily: SANS, fontWeight: "600" },
  defaultRadius: "md",
  components: {
    Card: { defaultProps: { radius: "lg", withBorder: true, shadow: "sm" } },
    Paper: { defaultProps: { radius: "lg" } },
    Button: { defaultProps: { radius: "md" } },
    Table: { defaultProps: { highlightOnHover: true, verticalSpacing: "sm" } },
    Modal: {
      defaultProps: { radius: "lg", centered: true, overlayProps: { blur: 2 } },
    },
  },
});

/** From client/src/pages/Login/constants.js — the brand palette. */
export const BRAND = Object.freeze({
  primary: "#15ABFF",
  dark: "#111111",
  danger: "#FA5252",
  surface: "#FFFFFF",
  surfaceAlt: "#F8F9FA",
  border: "#E9ECEF",
  gridLine: "#DEE2E6",
});
