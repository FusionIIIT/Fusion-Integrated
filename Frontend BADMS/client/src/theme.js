import { createTheme } from "@mantine/core";

const SANS =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

export const theme = createTheme({
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
    Modal: { defaultProps: { radius: "lg", centered: true, overlayProps: { blur: 2 } } },
  },
});
