/* ELM API service for client module. */import { SubmitLeaveApplicationDTO } from "./types";

export const submitLeaveApplication = async (
  dto: SubmitLeaveApplicationDTO
) => {
  // In a full implementation, this would make an HTTP request to the Django backend
  // For now, return a placeholder response
  return {
    id: 1,
    status: "submitted",
    ...dto,
  };
};

export const getLeaveCategories = async () => {
  // Placeholder - would fetch from API
  return [
    { code: "CL", label: "Casual Leave", entitlement_days: 8, carry_forward: false, continuous_counting: false },
    { code: "RH", label: "Restricted Holiday", entitlement_days: 2, carry_forward: false, continuous_counting: false },
    { code: "SCL", label: "Special Casual Leave", entitlement_days: 15, carry_forward: false, continuous_counting: false },
    { code: "EL", label: "Earned Leave", entitlement_days: 30, carry_forward: true, continuous_counting: true },
    { code: "VL", label: "Vacation Leave", entitlement_days: 60, carry_forward: false, continuous_counting: true },
    { code: "COL", label: "Casual Medical Leave", entitlement_days: 20, carry_forward: true, continuous_counting: true },
  ];
};

export const getEmployeeBalance = async (userId: number) => {
  // Placeholder - would fetch from API
  const categories = await getLeaveCategories();
  return categories.map((lc) => ({
    user_id: userId,
    leave_category_code: lc.code,
    remaining_days: lc.entitlement_days,
    used_days: 0,
  }));
};