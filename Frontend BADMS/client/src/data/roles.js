export const roles = [
    {
        id: 1,
        name: "System Admin",
        privileges: [
            "create_user",
            "delete_user",
            "reset_password",
            "edit_role",
            "create_custom_role",
            "archive_notifications",
            "archive_announcements",
            "archive_users",
            "manage_role_access",
            "bulk_import_users",
            "mail_credentials"
        ],
        description: "Has full control over the system.",
        timeOfCreation: "2022-01-01 10:00:00",
        createdBy: "superadmin",
        lastUpdated: "2023-09-30 14:00:00"
    },
    {
        id: 2,
        name: "Faculty",
        privileges: [
            "view_announcements",
            "manage_courses",
            "post_grades",
            "send_notifications"
        ],
        description: "Can manage their own courses and post grades for students.",
        timeOfCreation: "2022-05-10 11:30:00",
        createdBy: "system_admin",
        lastUpdated: "2023-09-15 12:45:00"
    },
    {
        id: 3,
        name: "Student",
        privileges: [
            "view_announcements",
            "register_for_courses",
            "view_timetable",
            "receive_grades"
        ],
        description: "Can view announcements, register for courses, and view their timetable.",
        timeOfCreation: "2022-07-15 09:15:00",
        createdBy: "system_admin",
        lastUpdated: "2023-08-25 10:35:00"
    },
    {
        id: 4,
        name: "Course Coordinator",
        privileges: [
            "create_course",
            "edit_course",
            "assign_instructors",
            "manage_timetable"
        ],
        description: "Manages course creation and assigns faculty members to courses.",
        timeOfCreation: "2022-06-20 13:40:00",
        createdBy: "system_admin",
        lastUpdated: "2023-09-10 14:30:00"
    },
    {
        id: 5,
        name: "Guest",
        privileges: [
            "view_announcements"
        ],
        description: "Can only view general announcements.",
        timeOfCreation: "2022-09-01 08:45:00",
        createdBy: "system_admin",
        lastUpdated: "2023-09-10 14:30:00"
    },
];