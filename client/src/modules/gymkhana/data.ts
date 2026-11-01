export type Club = {
  id: string;
  name: string;
  category: "Technical" | "Sports" | "Cultural";
  description: string;
  coordinator: string;
  facultyCouncillor: string;
  members: number;
  status: "Active" | "Pending";
};

export const clubs: Club[] = [
  {
    id: "coding",
    name: "Coding Club",
    category: "Technical",
    description: "A community for programming, problem-solving, hackathons and development activities.",
    coordinator: "Student Coordinator",
    facultyCouncillor: "Faculty Councillor",
    members: 85,
    status: "Active",
  },
  {
    id: "robotics",
    name: "Robotics Club",
    category: "Technical",
    description: "Explore robotics, embedded systems, automation and hands-on engineering projects.",
    coordinator: "Student Coordinator",
    facultyCouncillor: "Faculty Councillor",
    members: 52,
    status: "Active",
  },
  {
    id: "athletics",
    name: "Athletics Club",
    category: "Sports",
    description: "Promotes running, track and field events, fitness and sports participation.",
    coordinator: "Student Coordinator",
    facultyCouncillor: "Faculty Councillor",
    members: 64,
    status: "Active",
  },
  {
    id: "music",
    name: "Music Club",
    category: "Cultural",
    description: "A platform for students interested in singing, instruments and musical performances.",
    coordinator: "Student Coordinator",
    facultyCouncillor: "Faculty Councillor",
    members: 43,
    status: "Active",
  },
  {
    id: "photography",
    name: "Photography Club",
    category: "Cultural",
    description: "Brings together photography enthusiasts to learn, collaborate and document campus life.",
    coordinator: "Student Coordinator",
    facultyCouncillor: "Faculty Councillor",
    members: 38,
    status: "Pending",
  },
  {
    id: "literary",
    name: "Literary Club",
    category: "Cultural",
    description: "Encourages writing, reading, debates, creative expression and literary activities.",
    coordinator: "Student Coordinator",
    facultyCouncillor: "Faculty Councillor",
    members: 47,
    status: "Active",
  },
];
