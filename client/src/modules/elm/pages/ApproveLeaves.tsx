import React from 'react';

const ApproveLeaves = () => {
  // Fetch pending leave applications from backend and display them
  return (
    <div>
      <h1>Pending Leave Applications</h1>
      {/* List of pending leave applications */}
      {/* Each application should have a button to approve or reject */}
      <button>Approve</button>
      <button>Reject</button>
      {/* Add more buttons as needed */}
    </div>
  );
};

export default ApproveLeaves;