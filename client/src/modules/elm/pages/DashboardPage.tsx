import React from 'react';

const DashboardPage: React.FC = () => {
  return (
    <div className="p-4">
      <h1 className="text-2xl mb-4">Dashboard</h1>

      <div className="flex flex-wrap -mx-4">
        <div className="w-full md:w-1/2 xl:w-1/4 px-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg mb-2">Leave Balances</h2>
            <div>
              <p>CL: 10</p>
              <p>RH: 10</p>
              <p>SCL: 10</p>
              <p>EL: 10</p>
              <p>COL: 10</p>
              <p>VL: 10</p>
            </div>
          </div>
        </div>

        <div className="w-full md:w-1/2 xl:w-1/4 px-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg mb-2">Pending Applications</h2>
            <p>You have 5 pending leave applications.</p>
          </div>
        </div>

        <div className="w-full md:w-1/2 xl:w-1/4 px-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg mb-2">Substitute Requests</h2>
            <p>You have 3 substitute requests.</p>
          </div>
        </div>
      </div>

      <div className="flex justify-end mt-4">
        <button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Apply for Leave
        </button>
        <button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded ml-2">
          View History
        </button>
      </div>
    </div>
  );
};

export default DashboardPage;