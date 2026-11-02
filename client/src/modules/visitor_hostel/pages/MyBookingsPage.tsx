import React from 'react';
import { Table, Badge, Button, Title, Card, Stack } from '@mantine/core';

interface Booking {
    id: string;
    visitorName: string;
    dates: string;
    category: string;
    billing: number;
    status: 'pending' | 'confirmed' | 'cancelled';
}

const MyBookingsPage = () => {
    const data: Booking[] = [
        // Mock data here. Replace with actual data from your backend.
        { id: '1', visitorName: 'John Doe', dates: '01/02/2023 - 05/02/2023', category: 'Single Room', billing: 400, status: 'confirmed' },
    ];

    const handleCancel = (id: string) => {
        // Implement cancellation logic here. This could be an API call to your backend.
        console.log('Cancelling booking with id:', id);
    };

    return (
        <Stack>
            <Title order={2}>My Bookings</Title>
            <Card shadow="sm" padding="lg">
                <Table striped highlightOnHover>
                    <thead>
                        <tr>
                            <th>Booking ID</th>
                            <th>Visitor</th>
                            <th>Dates</th>
                            <th>Category</th>
                            <th>Billing</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((booking) => (
                            <tr key={booking.id}>
                                <td>{booking.id}</td>
                                <td>{booking.visitorName}</td>
                                <td>{booking.dates}</td>
                                <td>{booking.category}</td>
                                <td>{booking.billing}</td>
                                <td><Badge color="blue" variant="light">{booking.status}</Badge></td>
                                <td>
                                    <Button color="red" onClick={() => handleCancel(booking.id)}>Request Cancellation</Button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </Table>
            </Card>
        </Stack>
    );
};

export default MyBookingsPage;
