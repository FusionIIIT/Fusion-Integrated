import React from "react";

export const ElmPlaceholderPage: React.FC<{ title: string }> = ({ title }) => (
  <div style={{ padding: "2rem" }}>
    <h2>{title}</h2>
    <p>Employee Leave Management module view.</p>
  </div>
);

export default ElmPlaceholderPage;
