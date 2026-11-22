// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement_officer", grants: ["placement_officer"],
  },
  faculty: {
    username: "fac00001", role: "faculty", grants: ["faculty"],
  },
  hod: {
    username: "fac00020", role: "Head of Department", grants: ["Head of Department"],
  },
  deanRspc: {
    username: "stf00030", role: "Dean (RSPC)", grants: ["Dean (RSPC)"],
  },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
