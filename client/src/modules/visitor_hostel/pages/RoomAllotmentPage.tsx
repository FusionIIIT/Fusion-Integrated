import { Card, Title, Table, Button, Select, Badge, Group } from '@mantine/core';
import { useState } from 'react';

const RoomAllotmentPage = () => {
  const [selectedRoom, setSelectedRoom] = useState('');
  
  // This is a mock data. Replace it with your actual data.
  const roomsData = ['Room 1', 'Room 2', 'Room 3'];

  return (
    <Card shadow="sm" padding="lg">
      <Title order={2} mb="md">Approved Bookings Awaiting Room Allotment</Title>
      
      <Table withBorder withColumnBorders>
        <thead>
          <tr>
            <th>Booking ID</th>
            <th>Visitor Name</th>
            <th>Check-In Date</th>
            <th>Check-Out Date</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        
        {/* This is a mock data. Replace it with your actual data. */}
        <tbody>
          {[1, 2, 3].map((item) => (
            <tr key={item}>
              <td>#{item}</td>
              <td>Visitor #{item}</td>
              <td>01-01-2022</td>
              <td>01-02-2022</td>
              <td><Badge color="blue" variant="light">Pending</Badge></td>
              <td>
                <Select 
                  data={roomsData} 
                  value={selectedRoom}
                  onChange={setSelectedRoom}
                />
                
                <Group mt="md">
                  <Button color="blue">Allot Room</Button>
                  <Button color="green">Record Check-In</Button>
                  <Button color="red">Record Check-Out</Button>
                </Group>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
};

export default RoomAllotmentPage;
