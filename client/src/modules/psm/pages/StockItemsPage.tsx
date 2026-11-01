import React, { useState, useEffect } from 'react';
import { Paper, Title, Button, Modal, Group, Alert, Loader, Center } from '@mantine/core';
import { http, errorMessage } from '../../../lib/http';
import StockItemTable from '../components/StockItemTable';
import StockItemForm from '../components/StockItemForm';

interface StockItem {
  id: number;
  item_code: string;
  name: string;
  category: string;
  unit: string;
  available_quantity: number;
}

const StockItemsPage: React.FC = () => {
  const [items, setItems] = useState<StockItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openCreateModal, setOpenCreateModal] = useState(false);
  const [openEditModal, setOpenEditModal] = useState(false);
  const [editingItem, setEditingItem] = useState<StockItem | null>(null);

  const fetchItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await http.get('/psm/stock/');
      const data = res.data;
      setItems(Array.isArray(data) ? data : (data.results ?? []));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const handleCreate = async (item: Omit<StockItem, 'id'>) => {
    try {
      await http.post('/psm/stock/', item);
      setOpenCreateModal(false);
      await fetchItems();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const handleEdit = (item: StockItem) => {
    setEditingItem(item);
    setOpenEditModal(true);
  };

  const handleUpdate = async (item: Omit<StockItem, 'id'>) => {
    if (!editingItem) return;
    try {
      await http.put(`/psm/stock/${editingItem.id}/`, item);
      setOpenEditModal(false);
      setEditingItem(null);
      await fetchItems();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await http.delete(`/psm/stock/${id}/`);
      await fetchItems();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Paper shadow="sm" p="lg">
      <Group justify="space-between" mb="md">
        <Title order={2}>Stock Items</Title>
        <Button onClick={() => setOpenCreateModal(true)}>Create Stock Item</Button>
      </Group>

      {error && <Alert color="red" mb="md">{error}</Alert>}

      {loading ? (
        <Center py="xl"><Loader /></Center>
      ) : (
        <StockItemTable items={items} onEdit={handleEdit} onDelete={handleDelete} />
      )}

      <Modal opened={openCreateModal} onClose={() => setOpenCreateModal(false)} title="Create Stock Item">
        <StockItemForm onSubmit={handleCreate} onCancel={() => setOpenCreateModal(false)} />
      </Modal>

      <Modal opened={openEditModal} onClose={() => { setOpenEditModal(false); setEditingItem(null); }} title="Edit Stock Item">
        {editingItem && (
          <StockItemForm
            onSubmit={handleUpdate}
            onCancel={() => { setOpenEditModal(false); setEditingItem(null); }}
            initialData={editingItem}
          />
        )}
      </Modal>
    </Paper>
  );
};

export default StockItemsPage;
