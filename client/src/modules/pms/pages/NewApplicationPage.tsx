import { useState } from "react";
import {
  ActionIcon,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaTrash } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateApplication } from "../api/hooks";
import type { InventorInput } from "../api/types";

export default function NewApplicationPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState<string>("");
  const [abstract, setAbstract] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [claims, setClaims] = useState<string>("");
  const [domain, setDomain] = useState<string>("Computer Science & Engineering");
  const [filingType, setFilingType] = useState<string>("provisional");
  const [isConfidential, setIsConfidential] = useState<boolean>(false);

  const [inventors, setInventors] = useState<InventorInput[]>([
    {
      name: "Lead Inventor",
      email: "lead.inventor@institute.ac.in",
      department: "CSE",
      share_percentage: 100,
      is_lead: true,
    },
  ]);

  const createMutation = useCreateApplication();

  const handleAddInventor = () => {
    setInventors((prev) => [
      ...prev,
      {
        name: "",
        email: "",
        department: "",
        share_percentage: 0,
        is_lead: false,
      },
    ]);
  };

  const handleRemoveInventor = (index: number) => {
    if (inventors.length <= 1) return;
    setInventors((prev) => prev.filter((_, i) => i !== index));
  };

  const handleInventorChange = (index: number, field: keyof InventorInput, value: unknown) => {
    setInventors((prev) => {
      const copy = [...prev];
      if (field === "is_lead" && value === true) {
        copy.forEach((inv, i) => {
          inv.is_lead = i === index;
        });
      } else {
        (copy[index] as unknown as Record<string, unknown>)[field] = value;
      }
      return copy;
    });
  };

  const totalShare = inventors.reduce(
    (sum, inv) => sum + (Number(inv.share_percentage) || 0),
    0
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (totalShare !== 100) {
      notifications.show({
        color: "red",
        message: `Total inventor share percentage must equal 100% exactly (Current: ${totalShare}% / BR-PMS-006).`,
      });
      return;
    }

    try {
      const res = await createMutation.mutateAsync({
        title: title.trim(),
        abstract: abstract.trim(),
        description: description.trim(),
        claims: claims.trim(),
        domain,
        filing_type: filingType,
        is_confidential: isConfidential,
        inventors,
      });

      notifications.show({
        color: "green",
        message: `Patent application ${res.application_no} submitted successfully!`,
      });
      navigate("/pms/applications");
    } catch (err) {
      notifications.show({
        color: "red",
        message: errorMessage(err),
      });
    }
  };

  return (
    <Container size="lg" py="lg">
      <PageHeader
        title="Submit Patent Application"
        subtitle="Formal invention disclosure for patentability assessment, review, and statutory filing."
      />

      <form onSubmit={handleSubmit}>
        <Stack gap="lg">
          <Card withBorder p="lg">
            <FormSection
              first
              title="1. Invention Details"
              hint="Basic technical classification and title (BR-PMS-003, 007)"
            >
              <Stack gap="md" mt="md">
                <TextInput
                  label="Invention Title"
                  placeholder="Concise and precise technical title (max 200 chars)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />

                <Group grow>
                  <Select
                    label="Technical Domain"
                    value={domain}
                    onChange={(val) => setDomain(val ?? "Other")}
                    data={[
                      "Computer Science & Engineering",
                      "Electrical & Electronics",
                      "Mechanical Engineering",
                      "Chemical Sciences & Materials",
                      "Biotechnology & Medical Devices",
                      "Energy & Environmental Technologies",
                      "Civil & Structural Engineering",
                      "Other",
                    ]}
                    required
                  />

                  <Select
                    label="Filing Specification Type"
                    value={filingType}
                    onChange={(val) => setFilingType(val ?? "provisional")}
                    data={[
                      { value: "provisional", label: "Provisional Specification" },
                      { value: "complete", label: "Complete Specification" },
                    ]}
                    required
                  />
                </Group>

                <Checkbox
                  label="Confidential Invention Disclosure (Restricted Access / Section 35 Defense Interest)"
                  checked={isConfidential}
                  onChange={(e) => setIsConfidential(e.currentTarget.checked)}
                />
              </Stack>
            </FormSection>
          </Card>

          <Card withBorder p="lg">
            <FormSection
              title="2. Technical Disclosure & Claims"
              hint="Full description, summary, and statutory claim definitions (BR-PMS-004, 005)"
            >
              <Stack gap="md" mt="md">
                <Textarea
                  label="Technical Abstract"
                  description="Summary of the invention, problem solved, and primary embodiment (max 250 words / BR-PMS-004)"
                  placeholder="Describe the essence of the technical solution and its commercial utility..."
                  minRows={3}
                  value={abstract}
                  onChange={(e) => setAbstract(e.target.value)}
                  required
                />

                <Textarea
                  label="Detailed Description"
                  description="Background art, object of invention, detailed technical embodiments, and working examples."
                  placeholder="Provide sufficient disclosure to enable a person skilled in the art to replicate the invention..."
                  minRows={6}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />

                <Textarea
                  label="Patent Claims"
                  description="Distinct and clear technical boundaries of the monopoly sought (at least Claim 1 required / BR-PMS-005)."
                  placeholder="1. An apparatus for ... comprising: a first component configured to ...; and a second component ..."
                  minRows={5}
                  value={claims}
                  onChange={(e) => setClaims(e.target.value)}
                  required
                />
              </Stack>
            </FormSection>
          </Card>

          <Card withBorder p="lg">
            <FormSection
              title="3. Inventors & Royalty Revenue Share"
              hint="Every contributing inventor must be identified with share summing to 100% (BR-PMS-006)"
            >
              <Stack gap="md" mt="md">
                <Table withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Name</Table.Th>
                      <Table.Th>Email</Table.Th>
                      <Table.Th>Department</Table.Th>
                      <Table.Th style={{ width: 120 }}>Share (%)</Table.Th>
                      <Table.Th style={{ width: 90 }}>Lead</Table.Th>
                      <Table.Th style={{ width: 50 }}></Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {inventors.map((inv, idx) => (
                      <Table.Tr key={idx}>
                        <Table.Td>
                          <TextInput
                            value={inv.name}
                            onChange={(e) => handleInventorChange(idx, "name", e.target.value)}
                            placeholder="Full Name"
                            required
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            value={inv.email}
                            onChange={(e) => handleInventorChange(idx, "email", e.target.value)}
                            placeholder="email@domain.com"
                            type="email"
                            required
                          />
                        </Table.Td>
                        <Table.Td>
                          <TextInput
                            value={inv.department}
                            onChange={(e) => handleInventorChange(idx, "department", e.target.value)}
                            placeholder="Department"
                            required
                          />
                        </Table.Td>
                        <Table.Td>
                          <NumberInput
                            value={inv.share_percentage}
                            onChange={(val) => handleInventorChange(idx, "share_percentage", val)}
                            min={1}
                            max={100}
                            required
                          />
                        </Table.Td>
                        <Table.Td style={{ textAlign: "center" }}>
                          <Checkbox
                            checked={inv.is_lead}
                            onChange={(e) => handleInventorChange(idx, "is_lead", e.currentTarget.checked)}
                          />
                        </Table.Td>
                        <Table.Td>
                          <ActionIcon
                            color="red"
                            variant="subtle"
                            disabled={inventors.length <= 1}
                            onClick={() => handleRemoveInventor(idx)}
                          >
                            <FaTrash />
                          </ActionIcon>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>

                <Group justify="space-between">
                  <Button
                    variant="light"
                    leftSection={<FaPlus />}
                    size="xs"
                    onClick={handleAddInventor}
                  >
                    Add Co-Inventor
                  </Button>
                  <Text fw={600} size="sm" c={totalShare === 100 ? "teal" : "red"}>
                    Total Share: {totalShare}% {totalShare !== 100 && "(Must equal 100%)"}
                  </Text>
                </Group>
              </Stack>
            </FormSection>
          </Card>

          <Paper p="md" withBorder>
            <Group justify="flex-end">
              <Button variant="default" onClick={() => navigate("/pms/applications")}>
                Cancel
              </Button>
              <Button type="submit" color="blue" loading={createMutation.isPending}>
                Submit Patent Disclosure
              </Button>
            </Group>
          </Paper>
        </Stack>
      </form>
    </Container>
  );
}
