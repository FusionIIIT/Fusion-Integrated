import React, { useState } from 'react';
import axios from 'axios';

const CreateHostel = () => {
  const [name, setName] = useState('');
  const [active, setActive] = useState(true);

  const handleSubmit = e => {
    e.preventDefault();
    axios.post('/api/hostels/', { name, active })
      .then(() => {
        setName('');
        setActive(true);
      });
  };

  return (
    <div>
      <h1>Create Hostel</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Name:
          <input type="text" value={name} onChange={e => setName(e.target.value)} />
        </label>
        <label>
          Active:
          <input type="checkbox" checked={active} onChange={e => setActive(!active)} />
        </label>
        <button type="submit">Create</button>
      </form>
    </div>
  );
};

export default CreateHostel;
