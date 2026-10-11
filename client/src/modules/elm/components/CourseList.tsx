import React, { useEffect, useState } from 'react';
import { useQuery } from 'react-query';
import { Course } from '../types';
import { fetchCourses } from '../api';

const CourseList: React.FC = () => {
    const { data, isLoading, error } = useQuery<Course[]>('courses', fetchCourses);

    if (isLoading) return <div>Loading...</div>;
    if (error) return <div>Error: {error.message}</div>;

    return (
        <div>
            <h1>Courses</h1>
            <ul>
                {data.map(course => (
                    <li key={course.id}>{course.title}</li>
                ))}
            </ul>
        </div>
    );
};

export default CourseList;
