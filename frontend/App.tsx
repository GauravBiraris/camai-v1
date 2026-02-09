import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import CamerasView from './components/CamerasView';
import LogsView from './components/LogsView';
import { Monitor } from './types';
import { ENDPOINTS } from './config';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // FIX: Initialize with empty array [] instead of MOCK_MONITORS
  const [monitors, setMonitors] = useState<Monitor[]>([]); 
  const [logs, setLogs] = useState<any[]>([]);

  // 1. Fetch Monitors on Load
  useEffect(() => {
    fetch('http://127.0.0.1:5000/monitors')
      .then(res => res.json())
      .then(data => {
        console.log("Loaded Monitors:", data);
        setMonitors(data);
      })
      .catch(err => console.error("Failed to load monitors:", err));

      
// Fetch Logs
    fetch(ENDPOINTS.LOGS)
      .then(res => res.json())
      .then(data => setLogs(data))
      .catch(err => console.error(err));

  }, []);


  // HANDLERS
  const handleAddMonitor = (newMonitor: Monitor) => {
    setMonitors(prev => [...prev, newMonitor]);
  };

  const handleEditMonitor = (updatedMonitor: Monitor) => {
    setMonitors(prev => prev.map(m => m.id === updatedMonitor.id ? updatedMonitor : m));
  };

  const handleDeleteMonitor = (id: string) => {
    setMonitors(prev => prev.filter(m => m.id !== id));
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardView monitors={monitors} logs={logs} />;
      case 'cameras':
        return <CamerasView 
          monitors={monitors} 
          onAddMonitor={handleAddMonitor} 
          onEditMonitor={handleEditMonitor}
          onDeleteMonitor={handleDeleteMonitor}
        />;
      case 'logs':
        // Pass the logs state if you lift it, or keep LogsView self-contained
        return <LogsView />; 
      case 'settings':
        return (
            <div className="flex flex-col items-center justify-center h-[50vh] text-slate-400">
                <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                     <span className="text-2xl">⚙️</span>
                </div>
                <h3 className="text-lg font-medium text-slate-600">Settings</h3>
                <p>Global app configuration goes here.</p>
            </div>
        );
      default:
        return <DashboardView monitors={monitors} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 ml-64 p-8">
        <div className="max-w-6xl mx-auto">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default App;