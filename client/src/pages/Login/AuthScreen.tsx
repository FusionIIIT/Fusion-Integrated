import { useMemo, useState } from "react";
import { Box, Container, Transition } from "@mantine/core";
import { useMediaQuery, useReducedMotion } from "@mantine/hooks";

import AuthBackground from "./components/AuthBackground";
import BrandFooter from "./components/BrandFooter";
import BrandHeader from "./components/BrandHeader";
import LoginForm from "./components/LoginForm";
import WelcomePanel from "./components/WelcomePanel";
import { CONFIG } from "./constants";
import { useClock } from "./hooks/useClock";
import { useMousePosition } from "./hooks/useMousePosition";
import "./auth.css";

/**
 * The shared login composition, ported from Fusion_System_Administrator.
 *
 * Both doors render this, so they cannot drift apart — only the header tag,
 * the labels and the post target differ. Owns the landing↔login view state
 * and nothing else.
 */
export default function AuthScreen({
  tag, heading, identifierLabel, identifierPlaceholder, identifierType,
  onSubmit, loading, error, onClearError, shake, footer,
}: {
  tag: string;
  heading?: string;
  identifierLabel?: string;
  identifierPlaceholder?: string;
  identifierType?: string;
  onSubmit: (v: { username: string; password: string }) => void;
  loading: boolean;
  error: string | null;
  onClearError?: () => void;
  shake?: boolean;
  footer?: React.ReactNode;
}) {
  const isMobile = useMediaQuery(`(max-width: ${CONFIG.MOBILE_BREAKPOINT}px)`);
  const reducedMotion = useReducedMotion();
  const date = useClock();

  // On mobile we skip the landing splash and go straight to the form.
  const [view, setView] = useState<"landing" | "login">("landing");
  const isLogin = view === "login" || Boolean(isMobile);

  // The cursor glow only earns its keep on a desktop pointer with motion on.
  const glowEnabled = !isMobile && !reducedMotion;
  const mousePos = useMousePosition(glowEnabled);

  const containerStyle = useMemo(
    () => ({ animation: shake ? "fsaShake 0.5s ease-in-out" : "none" }),
    [shake],
  );

  return (
    <Box className="fsa-auth">
      <AuthBackground compact={isLogin} mousePos={mousePos} showGlow={glowEnabled} />

      <BrandHeader isMobile={Boolean(isMobile)} date={date} tag={tag} />

      <Box style={{
        flex: 1, display: "flex", position: "relative", overflow: "hidden",
      }}>
        <WelcomePanel isLogin={isLogin} onEnter={() => setView("login")} />

        <Box
          className="fsa-auth__login"
          style={{
            flex: isLogin ? 1 : 0,
            backgroundColor: "#FFFFFF",
            transition: "all 1s cubic-bezier(0.8, 0, 0.1, 1)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "auto",
          }}
        >
          <Transition mounted={isLogin} transition="slide-left" duration={600}>
            {(styles) => (
              <Container
                size={380} w="100%" className="fsa-auth__card"
                style={{ ...styles, maxHeight: "100%", overflowY: "auto" }}
              >
                <Box
                  className={shake ? "fsa-auth__shake" : ""}
                  style={containerStyle}
                >
                  <LoginForm
                    isMobile={Boolean(isMobile)}
                    loading={loading}
                    error={error}
                    onClearError={onClearError}
                    onSubmit={onSubmit}
                    onBack={isMobile ? undefined : () => setView("landing")}
                    heading={heading}
                    identifierLabel={identifierLabel}
                    identifierPlaceholder={identifierPlaceholder}
                    identifierType={identifierType}
                    footer={footer}
                  />
                </Box>
              </Container>
            )}
          </Transition>
        </Box>
      </Box>

      <BrandFooter />
    </Box>
  );
}
