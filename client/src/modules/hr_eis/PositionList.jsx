import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const PositionList = () => {
    const { data, isLoading, error } = useQuery({
        queryKey: ['positions'],
        queryFn: () => axios.get('/api/v1/hr-eis/positions/').then(response => response.data)
    });

    if (isLoading) return <div>Loading...</div>;
    if (error) return <div>Error: {error.message}</div>;

    return (
        <div>
            <h1>Position List</h1>
            <ul>
                {data.results.map(position => (
                    <li key={position.id}>{position.title}</li>
                ))}
            </ul>
        </div>
    );
};

export default PositionList;
