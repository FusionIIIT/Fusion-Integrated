/* eslint-disable react/prop-types */
import { useMemo, useState } from "react";
import {
  Box,
  Button,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
  UnstyledButton,
  rem,
} from "@mantine/core";
import { FaExclamationCircle } from "react-icons/fa";

const RequiredLabel = ({ children }) => (
  <Group gap={4} wrap="nowrap">
    <Text size="xs" fw={800} c="gray.6">
      {children}
    </Text>
    <Text size="xs" c="red" fw={700} style={{ lineHeight: 1 }}>
      *
    </Text>
  </Group>
);

const underlineStyle = (focused) => ({
  borderBottom: focused ? "2px solid #15ABFF" : "2px solid #E9ECEF",
  transition: "all 0.3s ease",
  background: focused
    ? "linear-gradient(90deg, rgba(21,171,255,0.03) 0%, transparent 100%)"
    : "transparent",
  paddingLeft: 10,
  paddingRight: 10,
});

/**
 * The credentials form. Purely presentational + local field state; it delegates the
 * actual authentication to `onSubmit`. No password reset here by design — operator
 * accounts are managed out-of-band in the system database.
 */
export default function LoginForm({
  isMobile,
  loading,
  error,
  onClearError,
  onSubmit,
  onBack,
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [focusField, setFocusField] = useState(null);

  const isValid = useMemo(
    () => username.trim().length > 0 && password.length > 0,
    [username, password],
  );

  // Dismiss a stale error as soon as the user starts correcting their input.
  const clearOnEdit = () => {
    if (error) onClearError?.();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!isValid || loading) return;
    onSubmit({ username, password });
  };

  return (
    <Stack gap={isMobile ? 18 : 30} style={{ paddingTop: 20, paddingBottom: 40 }}>
      <Box>
        <UnstyledButton
          onClick={onBack}
          mb={isMobile ? "sm" : "xl"}
          aria-label="Back to welcome screen"
          style={{ transition: "all 0.3s ease", display: "inline-block" }}
          onMouseEnter={(e) => (e.currentTarget.style.transform = "translateX(-5px)")}
          onMouseLeave={(e) => (e.currentTarget.style.transform = "translateX(0)")}
        >
          <Text size="xs" fw={900} c="blue" lts={1}>
            ← BACK
          </Text>
        </UnstyledButton>

        <Box style={{ position: "relative" }}>
          <Title order={2} fw={900} size={isMobile ? "28px" : "36px"} lts={-1}>
            Login
          </Title>
          <Box
            aria-hidden
            style={{
              position: "absolute",
              bottom: -5,
              left: 0,
              width: 60,
              height: 3,
              background: "linear-gradient(90deg, #15ABFF 0%, transparent 100%)",
              animation: "fsaSlideIn 0.5s ease-out, fsaGlow 2s ease-in-out infinite",
            }}
          />
        </Box>
      </Box>

      {error && (
        <Box
          role="alert"
          aria-live="assertive"
          p="sm"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            background: "linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)",
            color: "#fff",
            borderLeft: "4px solid rgba(0,0,0,0.15)",
            boxShadow: "0 8px 24px rgba(255,107,53,0.25)",
            animation: "fsaSlideIn 0.3s ease-out",
          }}
        >
          <FaExclamationCircle size={18} style={{ flexShrink: 0 }} />
          <Text size="sm" fw={600} style={{ lineHeight: 1.35 }}>
            {error}
          </Text>
        </Box>
      )}

      <form onSubmit={handleSubmit} noValidate>
        <Stack gap={isMobile ? "md" : "lg"}>
          <TextInput
            label={<RequiredLabel>USERNAME</RequiredLabel>}
            placeholder="Username / Roll No."
            variant="unstyled"
            size="lg"
            radius={0}
            value={username}
            onChange={(e) => {
              setUsername(e.currentTarget.value);
              clearOnEdit();
            }}
            onFocus={() => setFocusField("username")}
            onBlur={() => setFocusField(null)}
            autoComplete="username"
            autoFocus
            disabled={loading}
            style={underlineStyle(focusField === "username")}
          />

          <PasswordInput
            label={<RequiredLabel>PASSWORD</RequiredLabel>}
            placeholder="Password"
            variant="unstyled"
            size="lg"
            radius={0}
            value={password}
            onChange={(e) => {
              setPassword(e.currentTarget.value);
              clearOnEdit();
            }}
            onFocus={() => setFocusField("password")}
            onBlur={() => setFocusField(null)}
            autoComplete="current-password"
            disabled={loading}
            style={underlineStyle(focusField === "password")}
          />

          <Button
            fullWidth
            size="xl"
            radius={0}
            type="submit"
            loading={loading}
            disabled={!isValid}
            aria-label="Sign in"
            style={{
              height: rem(64),
              background: !isValid
                ? "linear-gradient(135deg, #E9ECEF 0%, #DEE2E6 100%)"
                : "linear-gradient(135deg, #111 0%, #15ABFF 100%)",
              transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
              boxShadow: !isValid ? "none" : "0 10px 30px rgba(21,171,255,0.3)",
              border: "none",
              cursor: !isValid ? "not-allowed" : "pointer",
            }}
            onMouseEnter={(e) => {
              if (!loading && isValid) {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "0 15px 40px rgba(21,171,255,0.5)";
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && isValid) {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 10px 30px rgba(21,171,255,0.3)";
              }
            }}
          >
            <Text fw={900} lts={2} c={!isValid ? "gray.5" : "white"}>
              {loading ? "AUTHENTICATING…" : "Login"}
            </Text>
          </Button>
        </Stack>
      </form>
    </Stack>
  );
}
