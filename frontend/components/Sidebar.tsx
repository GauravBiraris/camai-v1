import React from 'react';
import { LayoutDashboard, Camera, FileText, Settings, Activity } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'cameras', label: 'Cameras', icon: Camera },
    { id: 'logs', label: 'Logs', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="w-64 bg-slate-900 h-screen flex flex-col text-slate-300 fixed left-0 top-0 border-r border-slate-800 z-10">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Activity className="text-white w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold text-white tracking-tight">Visual AI</h1>
      </div>

      <nav className="flex-1 px-4 py-4 space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group ${
                isActive
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50'
                  : 'hover:bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-white'}`} />
              <span className="font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-500 to-blue-500 flex items-center justify-center text-xs font-bold text-white">
            JD
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-white">John Doe</span>
            <span className="text-xs text-slate-500">Admin</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
