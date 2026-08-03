/** Ported verbatim from Fusion_System_Administrator/client/src/theme.js.
 *  The two apps must look like one product, so this file is a copy, not a
 *  redesign. Change it there and here together, or not at all.
 *
 *  INPUT_DEFAULTS below is an addition rather than part of that port — form
 *  layout, not brand. The sysadmin console would benefit from the same. */
import { createTheme, type MantineThemeOverride } from "@mantine/core";

const SANS =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';

/** Help text renders BELOW the control, not above.
 *
 *  Mantine's default puts it above, which pushes the input down — so in a row
 *  where one field has a description and its neighbour does not, the two
 *  inputs sit at different heights. Every multi-column form in this app was
 *  visibly ragged because of it. */
const WRAPPER_ORDER = ["label", "input", "description", "error"] as const;

const INPUT_COMPONENTS = [
  "TextInput", "NumberInput", "Select", "MultiSelect", "Textarea",
  "TagsInput", "PasswordInput", "DateInput", "DateTimePicker", "Autocomplete",
];

const INPUT_DEFAULTS = Object.fromEntries(
  INPUT_COMPONENTS.map((name) => [
    name,
    { defaultProps: { inputWrapperOrder: WRAPPER_ORDER, size: "sm" } },
  ]),
);

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
    ...INPUT_DEFAULTS,
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
