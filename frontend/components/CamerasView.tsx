import React, { useState, useEffect, useRef } from 'react';
import { Monitor, MonitorType } from '../types';
import { Plus, X, Upload, Check, Video, MoreHorizontal, FileUp, Trash2, Edit2, Download } from 'lucide-react';
import { Link as LinkIcon, Copy } from 'lucide-react';
import { ENDPOINTS } from '../config';

interface CamerasViewProps {
  monitors: Monitor[];
  onAddMonitor: (monitor: Monitor) => void;
  onEditMonitor: (monitor: Monitor) => void;
  onDeleteMonitor: (id: string) => void;
}

const CamerasView: React.FC<CamerasViewProps> = ({ monitors, onAddMonitor, onEditMonitor, onDeleteMonitor }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  // Form State
  const [name, setName] = useState('');
  const [type, setType] = useState<MonitorType>('QUANTIFIER');
  const [source, setSource] = useState('RTSP Stream');
  const [rule, setRule] = useState('');
  const [integrations, setIntegrations] = useState<string[]>([]);
  
  // State for File Handling & Testing
  const [idealImageFile, setIdealImageFile] = useState<File | null>(null);
  const [testImageFile, setTestImageFile] = useState<File | null>(null); // To simulate a camera snap
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<any | null>(null);

  const integrationOptions = ['WhatsApp', 'Email', 'Excel Sheet'];
  const [connectionUrl, setConnectionUrl] = useState('0');
  const [interval, setIntervalVal] = useState('60'); // Default 60 minutes

  const [webhookModalOpen, setWebhookModalOpen] = useState(false);
  const [selectedWebhookMonitor, setSelectedWebhookMonitor] = useState<Monitor | null>(null);

  const toggleIntegration = (option: string) => {
    if (integrations.includes(option)) {
      setIntegrations(integrations.filter(i => i !== option));
    } else {
      setIntegrations([...integrations, option]);
    }
  };

  const resetForm = () => {
    setName('');
    setType('QUANTIFIER');
    setSource('RTSP Stream');
    setRule('');
    setIntegrations([]);
    setEditingId(null);
    setConnectionUrl('0');
    setIntervalVal('60');
  };

  const handleShowWebhook = (monitor: Monitor) => {
    setSelectedWebhookMonitor(monitor);
    setWebhookModalOpen(true);
    setActiveMenuId(null);
};
  const handleOpenAdd = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const handleOpenEdit = (monitor: Monitor) => {
    setName(monitor.name);
    setType(monitor.type);
    setSource(monitor.source);
    setRule(monitor.rule);
    setIntegrations(monitor.integrations);
    setEditingId(monitor.id);
    setActiveMenuId(null);
    setIsModalOpen(true);
    setConnectionUrl(monitor.connection_url || '0');
    setIntervalVal(monitor.interval?.toString() || '60');
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to permanently delete this monitor?')) {
      try {
        await fetch(`http://127.0.0.1:5000/monitors/${id}`, {
          method: 'DELETE'
        });
        onDeleteMonitor(id);
      } catch (err) {
        console.error("Failed to delete", err);
        // Fallback: update UI anyway if backend is unavailable but you want it gone from view
        onDeleteMonitor(id);
      }
    }
    setActiveMenuId(null);
  };

const handleDownloadBridge = (monitorId: string) => {
    // Direct link to the backend route triggers the download
    window.location.href = `${ENDPOINTS.MONITORS}/${monitorId}/download-bridge`;
    setActiveMenuId(null);
};

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('type', type);
    formData.append('source', source);
    formData.append('rule', rule);
    formData.append('integrations', integrations.join(','));
    formData.append('connection_url', connectionUrl);
    formData.append('interval', interval);
    
    if (idealImageFile) {
      formData.append('ideal_image', idealImageFile);
    }

    // Determine URL and Method based on Edit vs Create
    const url = editingId 
      ? `http://127.0.0.1:5000/monitors/${editingId}` 
      : 'http://127.0.0.1:5000/monitors';
    const method = editingId ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method: method,
        body: formData
      });
      
      if (!res.ok) throw new Error('Network response was not ok');
      
      const savedMonitor = await res.json();
      
      if (editingId) {
        onEditMonitor(savedMonitor);
      } else {
        onAddMonitor(savedMonitor);
      }
      
      setIsModalOpen(false);
      resetForm();
    } catch (err) {
      console.error("Failed to save", err);
      // For local development UI testing if backend is down:
      const fallbackMonitor: Monitor = {
        id: editingId || `m-${Math.random().toString(36).substr(2, 9)}`,
        name,
        type,
        source,
        status: 'OK',
        lastUpdate: 'Just now',
        rule,
        integrations,
        thumbnailUrl: `https://picsum.photos/400/225?random=${Math.floor(Math.random() * 100)}`
      };
      if (editingId) onEditMonitor(fallbackMonitor);
      else onAddMonitor(fallbackMonitor);
      setIsModalOpen(false);
      resetForm();
    }
  };

// The Bridge to Python Backend
  const handleTestLogic = async () => {
    if (!testImageFile) {
      alert("Please upload a 'Test Snapshot' to verify the logic.");
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const formData = new FormData();
      formData.append('mode', type); // QUANTIFIER, DETECTOR, PROCESS
      formData.append('rule', rule);
      formData.append('image', testImageFile); // The "Current" image
      
      if (idealImageFile) {
        formData.append('ideal_image', idealImageFile);
      }

      // Point this to Python Backend URL
      const response = await fetch('http://127.0.0.1:5000/trigger-scan', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setTestResult(data);
    } catch (error) {
      console.error("Connection Error:", error);
      setTestResult({ error: "Failed to connect to Backend. Is main.py running?" });
    } finally {
      setIsTesting(false);
    }
  };

  // Helper to handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, setFile: (f: File) => void) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Cameras & Monitors</h2>
          <p className="text-slate-500">Configure your visual analysis agents.</p>
        </div>
        <button 
          onClick={handleOpenAdd}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add New Monitor
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-visible shadow-sm min-h-[400px]">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Camera Name</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Class/Type</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Input Source</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase">Status</th>
              <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {monitors.map((monitor) => (
              <tr key={monitor.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded bg-slate-200 flex-shrink-0 overflow-hidden">
                      <img src={monitor.thumbnailUrl} alt="" className="w-full h-full object-cover" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{monitor.name}</p>
                      <p className="text-xs text-slate-500">{monitor.integrations.join(', ')}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    monitor.type === 'QUANTIFIER' ? 'bg-purple-100 text-purple-700' :
                    monitor.type === 'DETECTOR' ? 'bg-amber-100 text-amber-700' :
                    'bg-cyan-100 text-cyan-700'
                  }`}>
                    {monitor.type}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-slate-600">{monitor.source}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${monitor.status === 'OK' ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className={`text-sm font-medium ${monitor.status === 'OK' ? 'text-green-600' : 'text-red-600'}`}>
                      {monitor.status}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-right relative action-menu-container">
                  <button 
                    onClick={() => setActiveMenuId(activeMenuId === monitor.id ? null : monitor.id)}
                    className={`p-2 rounded-full transition-colors ${activeMenuId === monitor.id ? 'bg-slate-100 text-slate-600' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'}`}
                  >
                    <MoreHorizontal className="w-5 h-5" />
                  </button>
                  
                  {activeMenuId === monitor.id && (
                    <div className="absolute right-8 top-12 w-36 bg-white rounded-lg shadow-xl border border-slate-100 z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100 origin-top-right">
                      <div className="flex flex-col py-1">
<button 
                          onClick={() => handleDownloadBridge(monitor.id)}
                          className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 w-full text-left"
                        >
                          <Download className="w-4 h-4 text-slate-400" />
                          Download Bridge
                        </button>
                        <button 
    onClick={() => handleShowWebhook(monitor)}
    className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 w-full text-left"
  >
    <LinkIcon className="w-4 h-4 text-slate-400" />
    Integration API
  </button>
  
                        <button 
                          onClick={() => handleOpenEdit(monitor)}
                          className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2 w-full text-left"
                        >
                          <Edit2 className="w-4 h-4 text-slate-400" />
                          Edit
                        </button>
                        <button 
                          onClick={() => handleDelete(monitor.id)}
                          className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 w-full text-left"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add/Edit Monitor Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
              <h3 className="text-xl font-bold text-slate-900">{editingId ? 'Edit Monitor' : 'Add New Monitor'}</h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-full hover:bg-slate-100 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Monitor Name</label>
                  <input 
                    type="text" 
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Warehouse Entrance"
                    className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Class / Type</label>
                  <select 
                    value={type}
                    onChange={(e) => setType(e.target.value as MonitorType)}
                    className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white transition-all"
                  >
                    <option value="QUANTIFIER">Quantifier (Inventory)</option>
                    <option value="DETECTOR">Detector (Safety)</option>
                    <option value="PROCESS">Process (Progress)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Input Source</label>
                <select 
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white transition-all"
                >
                  <option value="RTSP Stream">RTSP Stream</option>
                  <option value="Upload Interval">Upload Interval (Images)</option>
                  <option value="Event Trigger">Event Trigger (API)</option>
                </select>
              </div>

 {/* Interval Configuration */}
{source !== 'Event Trigger' && (
  <div className="space-y-2">
    <label className="text-sm font-medium text-slate-700">
      Check Interval (Minutes)
      <span className="text-xs text-slate-400 ml-2">(0.5 = 30 seconds)</span>
    </label>
    <input 
      type="number" 
      step="0.1"
      min="0.1"
      value={interval}
      onChange={(e) => setIntervalVal(e.target.value)}
      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
    />
  </div>
)}             

{/*  Camera Connection Input */}
{source === 'RTSP Stream' && (
  <div className="space-y-2">
    <label className="text-sm font-medium text-slate-700">
       Camera ID or RTSP URL
       <span className="text-xs text-slate-400 ml-2">(Use '0' for USB Webcam)</span>
    </label>
    <input 
      type="text" 
      value={connectionUrl}
      onChange={(e) => setConnectionUrl(e.target.value)}
      placeholder="e.g., 0, 1, or rtsp://192.168.1.55/stream"
      className="w-full px-4 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
    />
  </div>
)}              

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 flex justify-between">
                  Natural Language Rule
                  <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded cursor-pointer">Generate with AI ✨</span>
                </label>
                <textarea 
                  value={rule}
                  onChange={(e) => setRule(e.target.value)}
                  placeholder="Example: Count the red bottles on the top shelf. Warn me if less than 5."
                  rows={4}
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none transition-all"
                />
              </div>

{/* UPDATED: Ideal State Upload */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Ideal State Reference (Optional)</label>
                <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 flex flex-col items-center justify-center text-slate-500 hover:border-blue-500 hover:bg-blue-50 transition-colors cursor-pointer relative">
                  <input 
                    type="file" 
                    accept="image/*"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={(e) => handleFileSelect(e, setIdealImageFile)}
                  />
                  <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                    <FileUp className="w-5 h-5 text-slate-400" />
                  </div>
                  <span className="text-sm font-medium">
                    {idealImageFile ? idealImageFile.name : "Click to upload reference image"}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-medium text-slate-700">Integrations</label>
                <div className="flex flex-wrap gap-3">
                  {integrationOptions.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => toggleIntegration(opt)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all flex items-center gap-2 ${
                        integrations.includes(opt)
                          ? 'bg-blue-50 border-blue-200 text-blue-700'
                          : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {integrations.includes(opt) && <Check className="w-4 h-4" />}
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
{/* NEW: Test & Verify Section */}
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-200 space-y-4">
                <h4 className="font-semibold text-slate-900 flex items-center gap-2">
                  <Video className="w-4 h-4 text-blue-600" />
                  Test Configuration
                </h4>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Test Image Upload */}
                  <div>
                    <label className="text-xs font-medium text-slate-600 block mb-1">Upload Sample Snapshot</label>
                    <input 
                      type="file" 
                      accept="image/*"
                      onChange={(e) => handleFileSelect(e, setTestImageFile)}
                      className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                  </div>

                  {/* Run Button */}
                  <div className="flex items-end">
<button 
  type="button"
  onClick={handleTestLogic}
  disabled={isTesting || !testImageFile}
  className={`w-full py-2 px-4 rounded-lg text-sm font-medium text-white transition-all flex justify-center items-center gap-2 ${
    isTesting ? 'bg-slate-400 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-700'
  }`}
>
  {isTesting ? (
    <>
      <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
      </svg>
      Analyzing...
    </>
  ) : (
    'Run Verification Test'
  )}
</button>
                  </div>
                </div>

                {/* Results Preview */}
                {testResult && (
                  <div className="mt-3 p-3 bg-slate-900 rounded-lg overflow-hidden">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-mono text-slate-400">JSON RESPONSE</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${testResult.error ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                        {testResult.error ? 'ERROR' : 'SUCCESS'}
                      </span>
                    </div>
                    <pre className="text-xs font-mono text-green-400 overflow-x-auto whitespace-pre-wrap max-h-40">
                      {JSON.stringify(testResult, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="pt-4 flex items-center justify-end gap-3">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)}
                  className="px-6 py-2.5 rounded-lg text-slate-700 font-medium hover:bg-slate-100 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="px-6 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 shadow-lg shadow-blue-500/30 transition-all transform active:scale-95"
                >
                  {editingId ? 'Update Monitor' : 'Create Monitor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Webhook Integration Modal */}
{webhookModalOpen && selectedWebhookMonitor && (
<div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
  <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg animate-in fade-in zoom-in duration-200">
    <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
      <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
        <LinkIcon className="w-5 h-5 text-blue-500" />
        Integration Webhook
      </h3>
      <button onClick={() => setWebhookModalOpen(false)} className="text-slate-400 hover:text-slate-600">
        <X className="w-5 h-5" />
      </button>
    </div>
    
    <div className="p-6 space-y-4">
      <p className="text-sm text-slate-600">
        Trigger this agent from external systems (POS, IoT Sensors, Mobile Apps) using this API endpoint.
      </p>

      {/* Scenario 1: Trigger via Signal (uses configured camera) */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Option A: Trigger Signal (Uses Camera {selectedWebhookMonitor.connection_url})
        </label>
        <div className="bg-slate-900 rounded-lg p-3 relative group">
          <code className="text-xs font-mono text-green-400 break-all block pr-8">
            curl -X POST http://127.0.0.1:5000/monitors/{selectedWebhookMonitor.id}/trigger
          </code>
          <button 
            className="absolute top-2 right-2 p-1.5 bg-slate-800 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            onClick={() => navigator.clipboard.writeText(`curl -X POST http://127.0.0.1:5000/monitors/${selectedWebhookMonitor.id}/trigger`)}
          >
            <Copy className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Scenario 2: Upload Image */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Option B: Upload Image (Overridden Input)
        </label>
        <div className="bg-slate-900 rounded-lg p-3 relative group">
          <code className="text-xs font-mono text-blue-400 break-all block pr-8">
            curl -X POST -F "image=@photo.jpg" http://127.0.0.1:5000/monitors/{selectedWebhookMonitor.id}/trigger
          </code>
        </div>
      </div>

      <div className="bg-blue-50 text-blue-800 text-xs p-3 rounded-lg">
        <strong>Tip:</strong> You can use this URL in Zapier, IFTTT, or your custom billing software to trigger a scan immediately when an event occurs.
      </div>
    </div>
  </div>
</div>
)}
    </div>
  );
};

export default CamerasView;