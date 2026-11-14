import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const EmployeeList = () => {
    const { data, isLoading, error } = useQuery({
        queryKey: ['employees'],
        queryFn: () => axios.get('/api/v1/hr-eis/employees/').then(response => response.data)
    });

    if (isLoading) return <div>Loading...</div>;
    if (error) return <div>Error: {error.message}</div>;

    return (
        <div>
            <h1>Employee List</h1>
            <ul>
                {data.results.map(employee => (
                    <li key={employee.id}>{employee.name}</li>
                ))}
            </ul>
        </div>
    );
};

export default EmployeeList;
