import React, { useEffect, useState } from 'react';
import { Clock, AlertTriangle, CheckCircle } from 'lucide-react';

// Define the shape of a Log Entry based on your backend JSON
interface LogEntry {
  id: string;
  monitor_name: string;
  type: 'QUANTIFIER' | 'DETECTOR' | 'PROCESS';
  timestamp: string;
  image_url: string;
  result: any; // The flexible JSON from Gemini
}

const LogsView: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    // Poll for logs every 5 seconds so user sees updates live
    const fetchLogs = () => {
      fetch('http://127.0.0.1:5000/logs')
        .then(res => res.json())
        .then(data => setLogs(data))
        .catch(err => console.error("Failed to fetch logs", err));
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderResultDetails = (log: LogEntry) => {
    if (log.type === 'QUANTIFIER') {
      return (
        <div className="mt-2 text-sm">
           <div className="flex gap-2 mb-2">
             <span className="font-semibold">Status:</span> 
             <span className={log.result.overall_status === 'OK' ? 'text-green-600' : 'text-red-600'}>
               {log.result.overall_status}
             </span>
           </div>
           {log.result.sections?.map((s: any, idx: number) => (
             <div key={idx} className="bg-slate-50 p-2 rounded mb-1 flex justify-between">
               <span>{s.section_id} ({s.detected_content})</span>
               <span className="font-mono">{s.current_value} {s.unit}</span>
             </div>
           ))}
        </div>
      );
    }
    if (log.type === 'DETECTOR') {
      return (
        <div className="mt-2 text-sm">
           <div className="flex gap-2 mb-2">
             <span className="font-semibold">Compliance:</span> 
             <span className={log.result.compliance_status === 'PASS' ? 'text-green-600' : 'text-red-600'}>
               {log.result.compliance_status}
             </span>
           </div>
           {log.result.detections?.map((d: any, idx: number) => (
             <div key={idx} className="flex gap-2 items-start">
               {d.is_compliant ? <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" /> : <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5" />}
               <span>{d.rule_checked}</span>
             </div>
           ))}
        </div>
      );
    }
    // PROCESS
    return (
        <div className="mt-2 text-sm">
           <div className="w-full bg-slate-200 rounded-full h-2.5 mb-2">
             <div className="bg-blue-600 h-2.5 rounded-full" style={{width: `${log.result.progress_percentage}%`}}></div>
           </div>
           <p className="font-medium text-slate-700">{log.result.current_stage} ({log.result.progress_percentage}%)</p>
           <p className="text-slate-500 text-xs mt-1">{log.result.visual_reasoning}</p>
        </div>
    );
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-900">Analysis History</h2>
      <div className="grid grid-cols-1 gap-6">
        {logs.map((log) => (
          <div key={log.id} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col md:flex-row gap-6">
            {/* Image Thumbnail */}
            <div className="w-full md:w-48 h-32 flex-shrink-0 rounded-lg overflow-hidden bg-slate-100 border border-slate-200">
              <img src={log.image_url} alt="Capture" className="w-full h-full object-cover" />
            </div>
            
            {/* Content */}
            <div className="flex-1">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-slate-800">{log.monitor_name}</h3>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                    <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{log.type}</span>
                    <Clock className="w-3 h-3" />
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
              
              {/* Dynamic Result Rendering */}
              <div className="mt-3 border-t border-slate-100 pt-3">
                {renderResultDetails(log)}
              </div>
            </div>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="text-center py-12 text-slate-400">No logs generated yet.</div>
        )}
      </div>
    </div>
  );
};

export default LogsView;