import React, { useEffect, useState } from "react";
import {
    Card,
    Title,
    Text,
    SimpleGrid,
    Loader,
    Alert
} from "@mantine/core";

const API_BASE = "/lms/courses/";

const CourseList = () => {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        fetch(API_BASE, {
            credentials: "include"
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Unable to load courses");
                }
                return response.json();
            })
            .then((data) => setCourses(data.courses || []))
            .catch((err) => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <Loader />;

    if (error) {
        return <Alert color="red">{error}</Alert>;
    }

    return (
        <div>
            <Title order={2} mb="lg">
                LMS - My Courses
            </Title>

            {courses.length === 0 ? (
                <Text>No courses available.</Text>
            ) : (
                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
                    {courses.map((course) => (
                        <Card
                            key={course.id}
                            shadow="sm"
                            padding="lg"
                            radius="md"
                            withBorder
                        >
                            <Title order={4}>
                                {course.course_name}
                            </Title>

                            <Text c="dimmed" size="sm">
                                {course.course_code}
                            </Text>

                            <Text mt="sm">
                                Role: {course.role}
                            </Text>
                        </Card>
                    ))}
                </SimpleGrid>
            )}
        </div>
    );
};

export default CourseList;