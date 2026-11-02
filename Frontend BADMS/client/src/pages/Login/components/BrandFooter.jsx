import { Box, Container, Group, Text } from "@mantine/core";

/** Slim footer with the animated accent line, matching the main Fusion client. */
export default function BrandFooter() {
  return (
    <Box
      p="lg"
      style={{
        borderTop: "1px solid #F1F3F5",
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.9) 0%, rgba(248,249,250,0.95) 100%)",
        backdropFilter: "blur(20px)",
        zIndex: 100,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <Box
        aria-hidden
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background:
            "linear-gradient(90deg, transparent 0%, #15ABFF 50%, transparent 100%)",
          backgroundSize: "200% 100%",
          animation: "fsaShimmer 3s ease-in-out infinite",
        }}
      />
      <Container size="xl">
        <Group justify="center" align="center" gap="sm">
          <Box
            aria-hidden
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: "#15ABFF",
              boxShadow: "0 0 10px rgba(21,171,255,0.5)",
              animation: "fsaPulse 2s ease-in-out infinite",
            }}
          />
          <Text
            size="xs"
            fw={800}
            c="gray.7"
            lts={1}
            style={{ fontFamily: "monospace" }}
          >
            PDPM IIITDM <span style={{ color: "#15ABFF" }}>JABALPUR</span>
          </Text>
        </Group>
      </Container>
    </Box>
  );
}
