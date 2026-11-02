/* eslint-disable react/prop-types */
import { Box, Container, Group, Text } from "@mantine/core";
import logoDesktop from "../../../assets/iiitdmj_logo.png";
import logoMobile from "../../../assets/IIITJ_logo.webp";

/**
 * Top bar: institute logo + name, and today's date. Mirrors the main Fusion client,
 * with a "SYSTEM ADMINISTRATOR" tag so operators always know which surface they are on.
 */
export default function BrandHeader({ isMobile, date }) {
  return (
    <Box
      p="md"
      style={{
        zIndex: 100,
        borderBottom: "2px solid #111",
        backgroundColor: "rgba(255,255,255,0.98)",
        backdropFilter: "blur(20px) saturate(180%)",
        boxShadow: "0 4px 30px rgba(0,0,0,0.05)",
        animation: "fsaSlideIn 0.8s ease-out",
      }}
    >
      <Container size="xl">
        <Group justify="space-between">
          <Group gap="md">
            <img
              src={isMobile ? logoMobile : logoDesktop}
              alt="PDPM IIITDM Jabalpur logo"
              style={{ height: 40 }}
            />
            <Box
              style={{
                borderLeft: "3px solid #15ABFF",
                paddingLeft: 15,
                paddingRight: 15,
                background:
                  "linear-gradient(90deg, rgba(21,171,255,0.05) 0%, transparent 100%)",
              }}
            >
              <Text fw={900} size="sm" lts={1} c="#111">
                PDPM IIITDM{" "}
                <span style={{ color: "#15ABFF" }}>JABALPUR</span>
              </Text>
              <Text
                size="xs"
                c="dimmed"
                fw={800}
                style={{ fontFamily: "monospace", letterSpacing: 2 }}
              >
                FUSION · SYSTEM ADMINISTRATOR
              </Text>
            </Box>
          </Group>
          <Group gap="sm" className="fsa-auth__status">
            <Text
              size="xs"
              c="dimmed"
              fw={800}
              style={{ fontFamily: "monospace" }}
            >
              {date}
            </Text>
          </Group>
        </Group>
      </Container>
    </Box>
  );
}
