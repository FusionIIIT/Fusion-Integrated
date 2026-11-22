import React, { useState, useEffect } from 'react';

interface Complaint {
  id: number;
  title: string;
  category: string;
  status: string;
  urgency: string;
  location: string;
}

export const IwdDashboard: React.FC = () => {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('CIVIL');
  const [location, setLocation] = useState('');

  useEffect(() => {
    fetch('/api/iwd/complaints/')
      .then((res) => res.json())
      .then((data) => setComplaints(data))
      .catch((err) => console.error(err));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch('/api/iwd/complaints/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Role': 'employee',
      },
      body: JSON.stringify({ title, description, category, location }),
    });
    if (res.ok) {
      const newComplaint = await res.json();
      setComplaints([newComplaint, ...complaints]);
      setTitle('');
      setDescription('');
      setLocation('');
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <header className="border-b pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Institute Works Department (IWD)</h1>
        <p className="text-sm text-gray-500">Civil and Electrical Maintenance Portal</p>
      </header>

      <section className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h2 className="text-lg font-semibold mb-4">Submit Maintenance Complaint</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Issue Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
              >
                <option value="CIVIL">Civil Infrastructure</option>
                <option value="ELECTRICAL">Electrical Infrastructure</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
              rows={3}
              required
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 font-medium"
          >
            Submit Requisition
          </button>
        </form>
      </section>

      <section className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h2 className="text-lg font-semibold mb-4">Maintenance Complaints Queue</h2>
        <div className="divide-y divide-gray-200">
          {complaints.map((c) => (
            <div key={c.id} className="py-3 flex justify-between items-center">
              <div>
                <p className="font-medium text-gray-900">{c.title}</p>
                <p className="text-xs text-gray-500">{c.category} &bull; {c.location}</p>
              </div>
              <span className="px-2 py-1 text-xs font-semibold rounded bg-blue-100 text-blue-800">
                {c.status}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default IwdDashboard;
