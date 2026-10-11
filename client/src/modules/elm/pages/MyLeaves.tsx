import React from 'react';
import { Link } from 'react-router-dom';

const MyLeaves = () => {
  // Fetch my leave applications from backend and display them
  return (
    <div>
      <h1>My Leave Applications</h1>
      {/* List of leave applications */}
      {/* Each application should have a link to view more details */}
      <Link to="/elm/my-leaves/1">View Application 1</Link>
      {/* Add more links as needed */}
    </div>
  );
};

export default MyLeaves;