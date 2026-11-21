import React from 'react';
import { Paper, Title, Table, Stack, Text } from '@mantine/core';
import { useMessMenu } from '../api/queries';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function MenuPage() {
  const { data: menuList } = useMessMenu();

  return (
    <Stack gap="md" p="md">
      <Title order={2}>Weekly Mess Menu</Title>
      <Paper p="md" withBorder radius="md">
        <Table striped withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Day</Table.Th>
              <Table.Th>Meal</Table.Th>
              <Table.Th>Items</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {menuList && menuList.length > 0 ? (
              menuList.map((m: any, idx: number) => (
                <Table.Tr key={idx}>
                  <Table.Td>{DAYS[m.day] || m.day}</Table.Td>
                  <Table.Td style={{ textTransform: 'capitalize' }}>{m.meal}</Table.Td>
                  <Table.Td>{m.items}</Table.Td>
                </Table.Tr>
              ))
            ) : (
              <Table.Tr>
                <Table.Td colSpan={3}><Text ta="center">No weekly menu entries published.</Text></Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Paper>
    </Stack>
  );
}