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
  pmsApplicant: { username: "stu00606", role: "ug_student", grants: [] },
  pmsApplicant2: { username: "stu00921", role: "ug_student", grants: [] },
  pmsDirector: { username: "fac00050", role: "pms_director", grants: ["pms_director"] },
  pmsDirector2: { username: "fac00040", role: "pms_director", grants: ["pms_director"] },
  pmsDirector3: { username: "fac00065", role: "pms_director", grants: ["pms_director"] },
  pmsPcc: { username: "stf00055", role: "pms_pcc_admin", grants: ["pms_pcc_admin"] },
  pmsAttorney: { username: "stf00057", role: "pms_attorney", grants: ["pms_attorney"] },
} as const satisfies Record<string, Account>;

export type AccountKey = keyof typeof ACCOUNTS;
