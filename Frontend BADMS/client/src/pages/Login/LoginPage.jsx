import { useEffect, useMemo, useState } from "react";
import { Box, Container, Transition } from "@mantine/core";
import { useMediaQuery, useReducedMotion } from "@mantine/hooks";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";
import AuthBackground from "./components/AuthBackground";
import BrandFooter from "./components/BrandFooter";
import BrandHeader from "./components/BrandHeader";
import LoginForm from "./components/LoginForm";
import WelcomePanel from "./components/WelcomePanel";
import { CONFIG } from "./constants";
import { useClock } from "./hooks/useClock";
import { useLogin } from "./hooks/useLogin";
import { useMousePosition } from "./hooks/useMousePosition";
import "./auth.css";

/**
 * Login screen orchestrator.
 *
 * Thin by design: it owns only the landing↔login view state and wires together the
 * presentational panels with the auth hooks. All the heavy lifting lives in
 * ./components and ./hooks, so this stays readable as the screen evolves.
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const isMobile = useMediaQuery(`(max-width: ${CONFIG.MOBILE_BREAKPOINT}px)`);
  const reducedMotion = useReducedMotion();
  const date = useClock();
  const { submit, loading, shake, error, clearError } = useLogin();

  // On mobile we skip the landing splash and go straight to the form.
  const [view, setView] = useState("landing"); // "landing" | "login"
  const isLogin = view === "login" || isMobile;

  // The cursor glow only earns its keep on a desktop pointer with motion enabled.
  const glowEnabled = !isMobile && !reducedMotion;
  const mousePos = useMousePosition(glowEnabled);

  // Already signed in? Don't show the login screen.
  useEffect(() => {
    if (isAuthenticated) navigate(CONFIG.POST_LOGIN_ROUTE, { replace: true });
  }, [isAuthenticated, navigate]);

  const containerStyle = useMemo(
    () => ({ animation: shake ? "fsaShake 0.5s ease-in-out" : "none" }),
    [shake],
  );

  return (
    <Box className="fsa-auth">
      <AuthBackground compact={isLogin} mousePos={mousePos} showGlow={glowEnabled} />

      <BrandHeader isMobile={isMobile} date={date} />

      <Box style={{ flex: 1, display: "flex", position: "relative", overflow: "hidden" }}>
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
                size={380}
                w="100%"
                className="fsa-auth__card"
                style={{ ...styles, maxHeight: "100%", overflowY: "auto" }}
              >
                <Box className={shake ? "fsa-auth__shake" : ""} style={containerStyle}>
                  <LoginForm
                    isMobile={isMobile}
                    loading={loading}
                    error={error}
                    onClearError={clearError}
                    onSubmit={submit}
                    onBack={() => setView("landing")}
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
