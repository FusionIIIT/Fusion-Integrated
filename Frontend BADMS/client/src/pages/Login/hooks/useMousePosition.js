import { useEffect, useRef, useState } from "react";
import { CONFIG } from "../constants";

/**
 * Tracks the pointer position for the decorative cursor glow.
 *
 * Performance: updates are throttled and the listener is only attached when
 * `enabled` is true (we disable it on mobile and when the user prefers reduced
 * motion), so it costs nothing when it isn't visible.
 */
export function useMousePosition(enabled = true) {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const lastRun = useRef(0);

  useEffect(() => {
    if (!enabled) return undefined;

    const onMove = (e) => {
      const now = Date.now();
      if (now - lastRun.current < CONFIG.MOUSE_THROTTLE_MS) return;
      lastRun.current = now;
      setPos({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [enabled]);

  return pos;
}
