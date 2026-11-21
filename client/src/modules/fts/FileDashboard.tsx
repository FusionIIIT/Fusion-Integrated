import type { FTSFile } from "./types";
import { TbInbox, TbSend, TbFileText, TbArchive, TbPlus } from "react-icons/tb";
import { Container, Title, Tabs, Table, Badge, Button, Group, Modal, TextInput } from "@mantine/core";
import { useState, useEffect } from "react";
import { http } from "../../lib/http";

const FileDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"inbox" | "outbox" | "drafts" | "archived">("inbox");
  const [inboxFiles, setInboxFiles] = useState<FTSFile[]>([]);
  const [outboxFiles, setOutboxFiles] = useState<FTSFile[]>([]);
  const [draftFiles, setDraftFiles] = useState<FTSFile[]>([]);
  const [archivedFiles, setArchivedFiles] = useState<FTSFile[]>([]);

  const [createOpened, setCreateOpened] = useState(false);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [initialComment, setInitialComment] = useState("");
  const [creatorRole, setCreatorRole] = useState("");

  const [forwardOpened, setForwardOpened] = useState(false);
  const [selectedFile, setSelectedFile] = useState<FTSFile | null>(null);
  const [forwardReceiverId, setForwardReceiverId] = useState("");
  const [forwardComment, setForwardComment] = useState("");
  const [forwardRole, setForwardRole] = useState("");

  const [returnOpened, setReturnOpened] = useState(false);
  const [returnComment, setReturnComment] = useState("");

  const [archiveOpened, setArchiveOpened] = useState(false);
  const [archiveComment, setArchiveComment] = useState("");

  const fetchFiles = () => {
    http.get<FTSFile[]>('/fts/inbox/').then((res) => setInboxFiles(res.data)).catch(() => {});
    http.get<FTSFile[]>('/fts/outbox/').then((res) => setOutboxFiles(res.data)).catch(() => {});
    http.get<FTSFile[]>('/fts/drafts/').then((res) => setDraftFiles(res.data)).catch(() => {});
    http.get<FTSFile[]>('/fts/archived/').then((res) => setArchivedFiles(res.data)).catch(() => {});
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleCreateSubmit = async () => {
    if (!initialComment.trim()) return;
    await http.post('/fts/files/', {
      subject,
      description,
      initial_comment: initialComment,
      creator_role: creatorRole,
    });
    setCreateOpened(false);
    setSubject("");
    setDescription("");
    setInitialComment("");
    setCreatorRole("");
    fetchFiles();
  };

  const handleForwardSubmit = async () => {
    if (!selectedFile || !forwardComment.trim() || !forwardReceiverId) return;
    await http.post(`/fts/files/${selectedFile.id}/forward/`, {
      receiver_id: Number(forwardReceiverId),
      comment: forwardComment,
      sender_role: forwardRole,
    });
    setForwardOpened(false);
    setForwardReceiverId("");
    setForwardComment("");
    setForwardRole("");
    fetchFiles();
  };

  const handleReturnSubmit = async () => {
    if (!selectedFile || !returnComment.trim()) return;
    await http.post(`/fts/files/${selectedFile.id}/return/`, {
      comment: returnComment,
    });
    setReturnOpened(false);
    setReturnComment("");
    fetchFiles();
  };

  const handleArchiveSubmit = async () => {
    if (!selectedFile) return;
    await http.post(`/fts/files/${selectedFile.id}/archive/`, {
      comment: archiveComment,
    });
    setArchiveOpened(false);
    setArchiveComment("");
    fetchFiles();
  };

  const handleDiscard = async (file: FTSFile) => {
    await http.post(`/fts/files/${file.id}/discard/`);
    fetchFiles();
  };

  const renderTable = (files: FTSFile[], type: "inbox" | "outbox" | "drafts" | "archived") => (
    <Table mt="md" striped highlightOnHover>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>File Number</Table.Th>
          <Table.Th>Subject</Table.Th>
          <Table.Th>Owner</Table.Th>
          <Table.Th>Current Holder</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Actions</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {files.map((file) => (
          <Table.Tr key={file.id}>
            <Table.Td>{file.file_number}</Table.Td>
            <Table.Td>{file.subject}</Table.Td>
            <Table.Td>{file.owner.username}</Table.Td>
            <Table.Td>{file.current_holder?.username || "—"}</Table.Td>
            <Table.Td>
              <Badge color={file.status === "circulated" ? "blue" : file.status === "archived" ? "gray" : "yellow"}>
                {file.status}
              </Badge>
            </Table.Td>
            <Table.Td>
              <Group gap="xs">
                {type === "inbox" && (
                  <>
                    <Button size="xs" onClick={() => { setSelectedFile(file); setForwardOpened(true); }}>Forward</Button>
                    <Button size="xs" color="orange" onClick={() => { setSelectedFile(file); setReturnOpened(true); }}>Return</Button>
                    <Button size="xs" color="gray" onClick={() => { setSelectedFile(file); setArchiveOpened(true); }}>Archive</Button>
                  </>
                )}
                {type === "drafts" && (
                  <>
                    <Button size="xs" onClick={() => { setSelectedFile(file); setForwardOpened(true); }}>Send</Button>
                    <Button size="xs" color="red" onClick={() => handleDiscard(file)}>Discard</Button>
                  </>
                )}
              </Group>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );

  return (
    <Container size="xl" py="lg">
      <Group justify="space-between" mb="lg">
        <Title order={2}>File Tracking System (FTS)</Title>
        <Button leftSection={<TbPlus size={16} />} onClick={() => setCreateOpened(true)}>
          Create File
        </Button>
      </Group>

      <Tabs value={activeTab} onChange={(val) => setActiveTab((val as any) || "inbox")}>
        <Tabs.List>
          <Tabs.Tab value="inbox" leftSection={<TbInbox size={16} />}>Inbox ({inboxFiles.length})</Tabs.Tab>
          <Tabs.Tab value="outbox" leftSection={<TbSend size={16} />}>Outbox ({outboxFiles.length})</Tabs.Tab>
          <Tabs.Tab value="drafts" leftSection={<TbFileText size={16} />}>Drafts ({draftFiles.length})</Tabs.Tab>
          <Tabs.Tab value="archived" leftSection={<TbArchive size={16} />}>Archived ({archivedFiles.length})</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="inbox">{renderTable(inboxFiles, "inbox")}</Tabs.Panel>
        <Tabs.Panel value="outbox">{renderTable(outboxFiles, "outbox")}</Tabs.Panel>
        <Tabs.Panel value="drafts">{renderTable(draftFiles, "drafts")}</Tabs.Panel>
        <Tabs.Panel value="archived">{renderTable(archivedFiles, "archived")}</Tabs.Panel>
      </Tabs>

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Create New File">
        <TextInput label="Subject" required value={subject} onChange={(e) => setSubject(e.target.value)} mb="md" />
        <TextInput label="Description" value={description} onChange={(e) => setDescription(e.target.value)} mb="md" />
        <TextInput label="Initial Comment" required value={initialComment} onChange={(e) => setInitialComment(e.target.value)} mb="md" />
        <TextInput label="Creator Role" value={creatorRole} onChange={(e) => setCreatorRole(e.target.value)} mb="md" />
        <Button fullWidth onClick={handleCreateSubmit}>Create</Button>
      </Modal>

      <Modal opened={forwardOpened} onClose={() => setForwardOpened(false)} title="Forward File">
        <TextInput label="Forward Comment" required value={forwardComment} onChange={(e) => setForwardComment(e.target.value)} mb="md" />
        <Button fullWidth onClick={handleForwardSubmit}>Forward</Button>
      </Modal>

      <Modal opened={returnOpened} onClose={() => setReturnOpened(false)} title="Return File">
        <TextInput label="Return Comment" required value={returnComment} onChange={(e) => setReturnComment(e.target.value)} mb="md" />
        <Button fullWidth onClick={handleReturnSubmit}>Return</Button>
      </Modal>

      <Modal opened={archiveOpened} onClose={() => setArchiveOpened(false)} title="Archive File">
        <TextInput label="Archive Comment" value={archiveComment} onChange={(e) => setArchiveComment(e.target.value)} mb="md" />
        <Button fullWidth onClick={handleArchiveSubmit}>Archive</Button>
      </Modal>
    </Container>
  );
};

export default FileDashboard;