import React, { useEffect, useState } from "react";
import { fetchWeeklyMenu } from "../api";
import { DailyMenuItem } from "../types";

const DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"];
const MEALS = ["BREAKFAST", "LUNCH", "DINNER"];

export const MenuPage: React.FC = () => {
  const [menuItems, setMenuItems] = useState<DailyMenuItem[]>([]);
  const [selectedDay, setSelectedDay] = useState<string>("MONDAY");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWeeklyMenu()
      .then((items) => setMenuItems(items))
      .finally(() => setLoading(false));
  }, []);

  const itemsForDay = menuItems.filter((i) => i.day_of_week === selectedDay);

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Mess Menu Schedule</h1>
        <p className="text-sm text-gray-500">Weekly recurring meal schedule for Central Mess</p>
      </div>

      {/* Day selector tabs */}
      <div className="flex space-x-2 border-b border-gray-200 pb-2 overflow-x-auto">
        {DAYS.map((day) => (
          <button
            key={day}
            onClick={() => setSelectedDay(day)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold uppercase ${
              selectedDay === day
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {day}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading menu items...</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {MEALS.map((meal) => {
            const item = itemsForDay.find((i) => i.meal_time === meal);
            return (
              <div key={meal} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <span className="inline-block rounded bg-indigo-50 px-2 py-0.5 text-xs font-bold text-indigo-700">
                  {meal}
                </span>
                <p className="mt-3 text-sm text-gray-700">
                  {item ? item.items : "No menu published for this slot."}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
