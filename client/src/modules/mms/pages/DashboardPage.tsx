import React, { useEffect, useState } from "react";
import { fetchMyRegistration, fetchMyRebates, fetchWeeklyMenu } from "../api";
import { DailyMenuItem, MessRegistration, RebateRequest } from "../types";

export const DashboardPage: React.FC = () => {
  const [registration, setRegistration] = useState<MessRegistration | null>(null);
  const [rebates, setRebates] = useState<RebateRequest[]>([]);
  const [menuItems, setMenuItems] = useState<DailyMenuItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [reg, rbs, menu] = await Promise.allSettled([
          fetchMyRegistration(),
          fetchMyRebates(),
          fetchWeeklyMenu(),
        ]);
        if (reg.status === "fulfilled") setRegistration(reg.value);
        if (rbs.status === "fulfilled") setRebates(rbs.value);
        if (menu.status === "fulfilled") setMenuItems(menu.value);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Mess Management System</h1>
        <p className="text-sm text-gray-500">Student Dining Dashboard & Meal Services</p>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading dashboard information...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Registration Status */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Registration Status</h2>
            {registration ? (
              <div className="space-y-2 text-sm">
                <p><strong>Mess Facility:</strong> {registration.mess_name}</p>
                <p><strong>Status:</strong> <span className="font-semibold text-indigo-600">{registration.status}</span></p>
                <p><strong>Period:</strong> {registration.start_date} to {registration.end_date || "End of Term"}</p>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No active registration found. Please register during the open window.</p>
            )}
          </div>

          {/* Rebates Summary */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Rebates Summary</h2>
            {rebates.length > 0 ? (
              <div className="space-y-2 text-sm">
                <p><strong>Total Applications:</strong> {rebates.length}</p>
                <p><strong>Approved Rebates:</strong> {rebates.filter((r) => r.status === "APPROVED").length}</p>
                <p><strong>Pending Decisions:</strong> {rebates.filter((r) => r.status === "PENDING").length}</p>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No rebate requests submitted yet.</p>
            )}
          </div>

          {/* Today's Menu Highlight */}
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm md:col-span-2">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Weekly Menu Overview</h2>
            {menuItems.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {menuItems.slice(0, 6).map((item) => (
                  <div key={item.id} className="rounded border border-gray-100 bg-gray-50 p-3 text-sm">
                    <p className="font-semibold text-gray-700">{item.day_of_week} - {item.meal_time}</p>
                    <p className="text-gray-600 text-xs mt-1">{item.items}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No menu items published yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
