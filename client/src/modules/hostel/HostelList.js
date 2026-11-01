import React, { useEffect, useState } from 'react';
import axios from 'axios';

const HostelList = () => {
  const [hostels, setHostels] = useState([]);

  useEffect(() => {
    axios.get('/api/hostels/')
      .then(response => {
        setHostels(response.data);
      });
  }, []);

  return (
    <div>
      <h1>Hostel List</h1>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {hostels.map(hostel => (
            <tr key={hostel.id}>
              <td>{hostel.name}</td>
              <td>{hostel.active ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default HostelList;
