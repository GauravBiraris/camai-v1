import React, { useMemo } from 'react';
import { Monitor } from '../types';
import { AlertTriangle, CheckCircle, Video, Activity } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface DashboardViewProps {
  monitors: Monitor[];
  logs: any[]; // NEW: Accept logs to calculate stats
}

const DashboardView: React.FC<DashboardViewProps> = ({ monitors, logs }) => {
  
  // 1. Calculate Real Stats
  const activeCameras = monitors.length;
  
  // Count alerts in the last 24 hours
  const alertsToday = useMemo(() => {
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    return logs.filter(log => {
      const logDate = new Date(log.timestamp);
      // Check if log is recent AND has an alert status
      const isAlert = 
        log.result?.overall_status !== 'OK' || 
        log.result?.compliance_status === 'FAIL' ||
        (log.result?.anomalies_detected && log.result.anomalies_detected.length > 0);
      return logDate > oneDayAgo && isAlert;
    }).length;
  }, [logs]);

  // 2. Prepare Chart Data (Group logs by Hour)
  const chartData = useMemo(() => {
    const data: Record<string, number> = {};
    // Initialize last 5 hours with 0
    for(let i=4; i>=0; i--) {
        const d = new Date();
        d.setHours(d.getHours() - i);
        const key = `${d.getHours()}:00`;
        data[key] = 0;
    }

    logs.forEach(log => {
        const date = new Date(log.timestamp);
        const key = `${date.getHours()}:00`;
        // Increment if this log represents an issue
        const isAlert = log.result?.overall_status !== 'OK' || log.result?.compliance_status === 'FAIL';
        if (isAlert && data[key] !== undefined) {
            data[key] += 1;
        }
    });

    return Object.keys(data).map(key => ({ name: key, alerts: data[key] }));
  }, [logs]);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Dashboard Overview</h2>
        <p className="text-slate-500">Live metrics from your {activeCameras} active monitors.</p>
      </div>

      {/* Summary Widgets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Alerts (24h)</p>
            <p className="text-3xl font-bold text-slate-900 mt-1">{alertsToday}</p>
          </div>
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${alertsToday > 0 ? 'bg-red-50' : 'bg-slate-50'}`}>
            <AlertTriangle className={`w-6 h-6 ${alertsToday > 0 ? 'text-red-500' : 'text-slate-400'}`} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">Active Monitors</p>
            <p className="text-3xl font-bold text-slate-900 mt-1">{activeCameras}</p>
          </div>
          <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center">
            <Video className="w-6 h-6 text-blue-500" />
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-500">System Status</p>
            <p className="text-3xl font-bold text-green-600 mt-1">Online</p>
          </div>
          <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center">
            <Activity className="w-6 h-6 text-green-500" />
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900 mb-6">Alert Frequency (Last 5 Hours)</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dy={10} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                <Tooltip cursor={{fill: '#f1f5f9'}} contentStyle={{ borderRadius: '8px' }} />
                <Bar dataKey="alerts" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Activity Mini-Feed */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col">
            <h3 className="text-lg font-semibold text-slate-900 mb-4">Latest Logs</h3>
            <div className="flex-1 overflow-y-auto space-y-4 max-h-64">
                {logs.slice(0, 5).map((log, i) => (
                    <div key={i} className="flex gap-3 items-start p-2 hover:bg-slate-50 rounded transition-colors">
                        <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                        <div>
                            <p className="text-sm font-medium text-slate-800">{log.monitor_name}</p>
                            <p className="text-xs text-slate-500">
                                {new Date(log.timestamp).toLocaleTimeString()}
                            </p>
                        </div>
                    </div>
                ))}
                {logs.length === 0 && <p className="text-sm text-slate-400">No activity yet.</p>}
            </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardView;