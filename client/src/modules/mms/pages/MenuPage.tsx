import React, { useEffect, useState } from "react";
import { getWeeklyMenu } from "../api";
import type { DailyMenuItem } from "../types";

export const MenuPage: React.FC = () => {
  const [menu, setMenu] = useState<DailyMenuItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWeeklyMenu()
      .then((data) => setMenu(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h2>Weekly Mess Menu</h2>
      {loading ? (
        <p>Loading menu...</p>
      ) : menu.length === 0 ? (
        <p>No menu items published yet.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "15px" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "8px" }}>Day</th>
              <th style={{ padding: "8px" }}>Meal</th>
              <th style={{ padding: "8px" }}>Menu Items</th>
            </tr>
          </thead>
          <tbody>
            {menu.map((item) => (
              <tr key={item.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "8px" }}>{item.day_of_week}</td>
                <td style={{ padding: "8px" }}>{item.meal_time}</td>
                <td style={{ padding: "8px" }}>{item.menu_description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default MenuPage;

