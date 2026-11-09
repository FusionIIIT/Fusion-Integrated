import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const DepartmentList = () => {
    const { data, isLoading, error } = useQuery({
        queryKey: ['departments'],
        queryFn: () => axios.get('/api/v1/hr-eis/departments/').then(response => response.data)
    });

    if (isLoading) return <div>Loading...</div>;
    if (error) return <div>Error: {error.message}</div>;

    return (
        <div>
            <h1>Department List</h1>
            <ul>
                {data.results.map(department => (
                    <li key={department.id}>{department.name}</li>
                ))}
            </ul>
        </div>
    );
};

export default DepartmentList;
