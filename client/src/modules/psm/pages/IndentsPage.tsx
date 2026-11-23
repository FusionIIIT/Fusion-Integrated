import React, { useState, useEffect } from 'react';
import { Paper, Title, Button, Modal, Group, Alert, Loader, Center } from '@mantine/core';
import { http, errorMessage } from '../../../lib/http';
import IndentTable from '../components/IndentTable';
import IndentForm from '../components/IndentForm';

interface Indent {
  id: number;
  indent_number: string;
  title: string;
  department: string;
  justification: string;
  total_estimated_cost: number;
  priority: string;
}

const IndentsPage: React.FC = () => {
  const [indents, setIndents] = useState<Indent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openCreateModal, setOpenCreateModal] = useState(false);
  const [openEditModal, setOpenEditModal] = useState(false);
  const [editingIndent, setEditingIndent] = useState<Indent | null>(null);

  const fetchIndents = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await http.get('/psm/indents/');
      const data = res.data;
      setIndents(Array.isArray(data) ? data : (data.results ?? []));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIndents();
  }, []);

  const handleCreate = async (indent: Omit<Indent, 'id'>) => {
    try {
      await http.post('/psm/indents/', indent);
      setOpenCreateModal(false);
      await fetchIndents();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const handleEdit = (indent: Indent) => {
    setEditingIndent(indent);
    setOpenEditModal(true);
  };

  const handleUpdate = async (indent: Omit<Indent, 'id'>) => {
    if (!editingIndent) return;
    try {
      await http.put(`/psm/indents/${editingIndent.id}/`, indent);
      setOpenEditModal(false);
      setEditingIndent(null);
      await fetchIndents();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await http.delete(`/psm/indents/${id}/`);
      await fetchIndents();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Paper shadow="sm" p="lg">
      <Group justify="space-between" mb="md">
        <Title order={2}>Purchase Indents</Title>
        <Button onClick={() => setOpenCreateModal(true)}>Create Purchase Indent</Button>
      </Group>

      {error && <Alert color="red" mb="md">{error}</Alert>}

      {loading ? (
        <Center py="xl"><Loader /></Center>
      ) : (
        <IndentTable indents={indents} onEdit={handleEdit} onDelete={handleDelete} />
      )}

      <Modal opened={openCreateModal} onClose={() => setOpenCreateModal(false)} title="Create Purchase Indent">
        <IndentForm onSubmit={handleCreate} onCancel={() => setOpenCreateModal(false)} />
      </Modal>

      <Modal opened={openEditModal} onClose={() => { setOpenEditModal(false); setEditingIndent(null); }} title="Edit Purchase Indent">
        {editingIndent && (
          <IndentForm
            onSubmit={handleUpdate}
            onCancel={() => { setOpenEditModal(false); setEditingIndent(null); }}
            initialData={editingIndent}
          />
        )}
      </Modal>
    </Paper>
  );
};

export default IndentsPage;
