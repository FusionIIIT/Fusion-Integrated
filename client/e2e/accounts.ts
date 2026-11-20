// Synthetic fusion-dev.dump accounts. Global setup grants each one its `grants` in the IAM.
export const PASSWORD = process.env.E2E_PASSWORD ?? "fusion123";

export interface Account {
  username: string;
  role: string;
  grants: readonly string[];
}

export const ACCOUNTS = {
  student: { username: "stu00001", role: "ug_student", grants: [] },
  applicant: { username: "stu00002", role: "ug_student", grants: [] },
  placementOfficer: {
    username: "stf00062", role: "placement officer", grants: ["placement officer"],
  },
  placementChairman: {
    username: "fac00001", role: "placement chairman", grants: ["placement chairman"],
  },
  alumnus: { username: "stu00003", role: "alumini", grants: ["alumini"] },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
