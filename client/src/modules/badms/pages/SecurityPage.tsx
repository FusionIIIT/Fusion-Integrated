import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { FaCheck, FaExclamationTriangle, FaLock, FaShieldAlt } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { ArchivalRequest } from "../api";
import { useArchives, useConfigureEncryption } from "../api";
import { BadmsStatusBadge } from "../components/BadmsStatusBadge";

export default function SecurityPage() {
  const { data: routedData, isLoading: loadingRouted } = useArchives({
    status: "routed_to_security",
  });
  const { data: allArchivesData } = useArchives();
  const encryptMutation = useConfigureEncryption();

  const [encryptTarget, setEncryptTarget] = useState<ArchivalRequest | null>(null);
  const [algorithm, setAlgorithm] = useState("AES-256-GCM");
  const [keyId, setKeyId] = useState("KEY-AES256-SEC-01");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleEncryptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!encryptTarget) return;

    setErrorMsg("");
    setSuccessMsg("");
    try {
      await encryptMutation.mutateAsync({
        id: encryptTarget.id,
        payload: { algorithm, key_id: keyId },
      });
      setSuccessMsg(
        `Archive #${encryptTarget.id} (${encryptTarget.file_name}) successfully encrypted with ${algorithm}.`,
      );
      setEncryptTarget(null);
    } catch (err: any) {
      setErrorMsg(
        err?.response?.data?.detail ||
          err?.response?.data?.error?.message ||
          "Failed to configure encryption.",
      );
    }
  };

  const pendingEncryption = routedData?.results || [];
  const encryptedArchives =
    allArchivesData?.results?.filter((r) => r.is_encrypted) || [];

  return (
    <Stack gap="lg">
      <PageHeader
        title="IT Security & Encryption Policy"
        subtitle="Manage cryptographic controls, AES-256 encryption at rest and in transit for sensitive archives"
      />

      <Alert icon={<FaShieldAlt size={14} />} color="teal">
        Security Standard Enforced: Sensitive archives are cryptographically protected using
        industry-standard AES-256 encryption at rest and in transit. Integrity digests (SHA-256)
        are verified prior to storage.
      </Alert>

      {successMsg && (
        <Alert icon={<FaCheck size={14} />} color="green" withCloseButton onClose={() => setSuccessMsg("")}>
          {successMsg}
        </Alert>
      )}

      {errorMsg && (
        <Alert icon={<FaExclamationTriangle size={14} />} color="red" withCloseButton onClose={() => setErrorMsg("")}>
          {errorMsg}
        </Alert>
      )}

      {/* Sensitive Archives Awaiting Encryption Table */}
      <Card withBorder padding="md" radius="md">
        <Text fw={600} size="md" mb="md">
          Sensitive Archives Awaiting Encryption Configuration ({pendingEncryption.length})
        </Text>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>File Name</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>SysAdmin Classified</Table.Th>
                <Table.Th>Size</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Action</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {loadingRouted ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    Loading pending security requests...
                  </Table.Td>
                </Table.Tr>
              ) : pendingEncryption.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    No sensitive archives currently awaiting encryption configuration.
                  </Table.Td>
                </Table.Tr>
              ) : (
                pendingEncryption.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>#{req.id}</Table.Td>
                    <Table.Td fw={500}>{req.file_name}</Table.Td>
                    <Table.Td>{req.department}</Table.Td>
                    <Table.Td>
                      {req.sysadmin_classified_at
                        ? new Date(req.sysadmin_classified_at).toLocaleDateString()
                        : "Classified"}
                    </Table.Td>
                    <Table.Td>{(req.file_size_bytes / 1024).toFixed(1)} KB</Table.Td>
                    <Table.Td>
                      <BadmsStatusBadge value={req.status} />
                    </Table.Td>
                    <Table.Td>
                      <Button
                        size="xs"
                        color="teal"
                        leftSection={<FaLock size={14} />}
                        onClick={() => {
                          setEncryptTarget(req);
                          setAlgorithm("AES-256-GCM");
                          setKeyId("KEY-AES256-SEC-01");
                        }}
                      >
                        Configure AES-256
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {/* Encrypted Archives Table */}
      <Card withBorder padding="md" radius="md">
        <Text fw={600} size="md" mb="md">
          Cryptographically Protected Archives ({encryptedArchives.length})
        </Text>
        <Table.ScrollContainer minWidth={800}>
          <Table striped highlightOnHover verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>File Name</Table.Th>
                <Table.Th>Department</Table.Th>
                <Table.Th>Encryption Algorithm</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Protection</Table.Th>
                <Table.Th>Configured At</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {encryptedArchives.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                    No encrypted archives in repository.
                  </Table.Td>
                </Table.Tr>
              ) : (
                encryptedArchives.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>#{req.id}</Table.Td>
                    <Table.Td fw={500}>{req.file_name}</Table.Td>
                    <Table.Td>{req.department}</Table.Td>
                    <Table.Td>
                      <Text fw={600} size="xs" c="teal">
                        {req.encryption_algorithm}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <BadmsStatusBadge value={req.status} />
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4}>
                        <FaCheck size={14} color="green" />
                        <Text size="xs" c="green">
                          Rest & Transit
                        </Text>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      {req.security_configured_at
                        ? new Date(req.security_configured_at).toLocaleString()
                        : "-"}
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {/* Encryption Configuration Modal */}
      <Modal
        opened={Boolean(encryptTarget)}
        onClose={() => setEncryptTarget(null)}
        title={`Configure AES-256 for #${encryptTarget?.id}: ${encryptTarget?.file_name}`}
      >
        <form onSubmit={handleEncryptSubmit}>
          <Stack gap="md">
            <Text size="sm">
              Applying institutional cryptographic protection to sensitive research/departmental
              archive.
            </Text>

            <Select
              label="Encryption Cipher & Mode"
              data={[
                { value: "AES-256-GCM", label: "AES-256-GCM (Authenticated AEAD - Recommended)" },
                { value: "AES-256-CBC", label: "AES-256-CBC (Cipher Block Chaining with PBKDF2)" },
              ]}
              required
              value={algorithm}
              onChange={(val) => setAlgorithm(val || "AES-256-GCM")}
            />

            <TextInput
              label="KMS Key Identifier"
              placeholder="e.g. KEY-AES256-SEC-01"
              required
              value={keyId}
              onChange={(e) => setKeyId(e.target.value)}
            />

            <Alert icon={<FaLock size={14} />} color="teal">
              The archive will be transformed with AES-256 encryption at rest and in transit.
              Status will transition to <strong>ENCRYPTED ARCHIVE CREATED</strong>.
            </Alert>

            <Group justify="flex-end">
              <Button variant="default" onClick={() => setEncryptTarget(null)}>
                Cancel
              </Button>
              <Button
                type="submit"
                color="teal"
                leftSection={<FaLock size={14} />}
                loading={encryptMutation.isPending}
              >
                Apply Encryption Policy
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Stack>
  );
}
