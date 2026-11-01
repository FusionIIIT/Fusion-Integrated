/* eslint-disable react/prop-types */
import { Box, Stack, Text, Title, UnstyledButton, rem } from "@mantine/core";

/**
 * The "WELCOME TO FUSION" hero panel. On the landing view it fills the screen with a
 * CTA; once the user enters, it shrinks to a slim accent column beside the form.
 */
export default function WelcomePanel({ isLogin, onEnter }) {
  return (
    <Box
      className={`fsa-auth__welcome ${isLogin ? "fsa-auth__welcome--minimized" : ""}`}
      style={{
        width: isLogin ? "35%" : "100%",
        height: "100%",
        transition: "all 1s cubic-bezier(0.8, 0, 0.1, 1)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: isLogin ? "40px 40px 40px 20px" : "0 10%",
        background: isLogin
          ? "linear-gradient(135deg, rgba(248,249,250,0.2) 0%, rgba(255,255,255,0.25) 100%)"
          : "transparent",
        boxShadow: isLogin ? "10px 0 30px rgba(0,0,0,0.05)" : "none",
        zIndex: 20,
        position: "relative",
      }}
    >
      {isLogin && (
        <Box
          aria-hidden
          style={{
            position: "absolute",
            right: 0,
            top: "10%",
            bottom: "10%",
            width: 4,
            background:
              "linear-gradient(180deg, transparent 0%, #15ABFF 50%, transparent 100%)",
            borderRadius: 2,
            animation: "fsaGlow 2s ease-in-out infinite",
            zIndex: 30,
          }}
        />
      )}

      <Stack gap={0} style={{ animation: "fsaSlideIn 0.8s ease-out" }}>
        <Text
          fw={900}
          className="fsa-auth__outline"
          style={{
            fontSize: isLogin ? rem(60) : rem(200),
            lineHeight: 0.7,
            letterSpacing: isLogin ? "1px" : "-10px",
            color: "transparent",
            WebkitTextStroke: isLogin ? "3.5px #64f5f5" : "3px #DEE2E6",
            WebkitTextFillColor: "transparent",
            transition: "all 1s ease",
          }}
        >
          WELCOME
        </Text>

        <Box mt={isLogin ? 10 : -30}>
          <Box style={{ display: "inline-block" }}>
            <Text
              size={isLogin ? rem(20) : rem(48)}
              fw={900}
              lts={-1}
              ta="center"
              className="fsa-auth__to"
              style={{
                marginBottom: isLogin ? -5 : -15,
                background: "linear-gradient(135deg, #15ABFF 0%, #111 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              TO
            </Text>
            <Title
              order={1}
              fw={900}
              size={isLogin ? rem(28) : rem(64)}
              lts={-2}
              className="fsa-auth__title"
              style={{
                background: "linear-gradient(135deg, #111 0%, #15ABFF 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              FUSION
            </Title>
          </Box>
        </Box>

        {!isLogin && (
          <Box>
            <UnstyledButton
              onClick={onEnter}
              mt={80}
              aria-label="Proceed to login"
              style={{
                padding: "24px 80px",
                background: "linear-gradient(135deg, #111 0%, #15ABFF 100%)",
                color: "#FFF",
                transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                width: "fit-content",
                boxShadow: "0 10px 40px rgba(21,171,255,0.3)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "0 15px 50px rgba(21,171,255,0.5)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 10px 40px rgba(21,171,255,0.3)";
              }}
            >
              <Text fw={900} lts={4} size="sm">
                Login →
              </Text>
            </UnstyledButton>
          </Box>
        )}
      </Stack>
    </Box>
  );
}
