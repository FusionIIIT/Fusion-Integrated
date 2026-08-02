import { useEffect, useState } from "react";

import { CONFIG } from "../constants";

/** Cursor position for the decorative glow, throttled so it cannot flood React
 *  with renders. Returns a static point when disabled. */
export function useMousePosition(enabled: boolean) {
  const [pos, setPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!enabled) return;
    let last = 0;
    const onMove = (e: MouseEvent) => {
      const now = Date.now();
      if (now - last < CONFIG.MOUSE_THROTTLE_MS) return;
      last = now;
      setPos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, [enabled]);

  return pos;
}
