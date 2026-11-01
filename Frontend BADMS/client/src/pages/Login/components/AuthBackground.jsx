/* eslint-disable react/prop-types */
import { Box } from "@mantine/core";
import { BRAND } from "../constants";

/**
 * Decorative animated backdrop: a fine grid, a slow floating orb, and a cursor-
 * following glow. Purely cosmetic and pointer-events:none so it never intercepts
 * clicks. The caller decides whether the cursor glow is shown (it's disabled on
 * mobile / reduced-motion for performance).
 */
export default function AuthBackground({ compact, mousePos, showGlow }) {
  return (
    <>
      {showGlow && (
        <Box
          aria-hidden
          style={{
            position: "absolute",
            top: mousePos.y - 200,
            left: mousePos.x - 200,
            width: 400,
            height: 400,
            background:
              "radial-gradient(circle, rgba(21,171,255,0.08) 0%, transparent 70%)",
            borderRadius: "50%",
            pointerEvents: "none",
            transition: "all 0.3s ease-out",
            zIndex: 1,
          }}
        />
      )}

      <Box
        aria-hidden
        style={{
          position: "absolute",
          top: "20%",
          right: "10%",
          width: 600,
          height: 600,
          background:
            "radial-gradient(circle, rgba(21,171,255,0.05) 0%, transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
          animation: "fsaFloat 20s ease-in-out infinite",
          zIndex: 1,
        }}
      />

      <Box
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 0,
          opacity: 0.3,
          backgroundImage: `
            repeating-linear-gradient(45deg, ${BRAND.gridLine}, ${BRAND.gridLine} 1px, transparent 1px, transparent ${compact ? "20px" : "100px"}),
            radial-gradient(${BRAND.gridLine} 1.2px, transparent 1.2px)
          `,
          backgroundSize: compact ? "20px 20px, 20px 20px" : "100px 100px, 40px 40px",
          transition: "all 1.5s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      />
    </>
  );
}
