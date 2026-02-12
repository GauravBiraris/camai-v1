import React, { useState } from 'react';
import { ENDPOINTS } from '../config';

const AddMonitorModal = ({ isOpen, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    mode: 'QUANTIFIER', // Default
    rule: '',
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleTestConnection = async () => {
    if (!selectedFile || !formData.rule) {
      alert("Please select a file and enter a rule first.");
      return;
    }

    setIsLoading(true);
    setTestResult(null);

    // 1. Prepare Data for Backend
    const data = new FormData();
    data.append('mode', formData.mode);
    data.append('rule', formData.rule);
    data.append('test_image', selectedFile);

    try {
      // 2. Hit the Backend API
      const response = await fetch(`${ENDPOINTS.TRIGGER}`, {
        method: 'POST',
        body: data,
      });

      const result = await response.json();
      
      // 3. Handle Result
      if (response.ok) {
        setTestResult(result.gemini_response);
      } else {
        alert("Error: " + result.error);
      }
    } catch (error) {
      console.error("Connection failed", error);
      alert("Could not connect to Backend server (Is it running on port 5000?)");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center p-4">
      <div className="bg-gray-800 text-white p-6 rounded-lg w-full max-w-2xl overflow-y-auto max-h-[90vh]">
        <h2 className="text-xl font-bold mb-4">Add New Monitor</h2>
        
        {/* --- FORM FIELDS --- */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Monitor Name</label>
            <input 
              className="w-full p-2 rounded bg-gray-700 border border-gray-600 focus:border-blue-500 outline-none"
              type="text" 
              placeholder="e.g. Shelf A, Front Gate"
              onChange={(e) => setFormData({...formData, name: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Logic Class</label>
            <select 
              className="w-full p-2 rounded bg-gray-700 border border-gray-600"
              value={formData.mode}
              onChange={(e) => setFormData({...formData, mode: e.target.value})}
            >
              <option value="QUANTIFIER">Quantifier (Inventory/Counts)</option>
              <option value="DETECTOR">Detector (Safety/Compliance)</option>
              <option value="PROCESS">Process Monitor (Progress)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Ideal State / Sample Image</label>
            <input 
              type="file" 
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Natural Language Rule</label>
            <textarea 
              className="w-full p-2 rounded bg-gray-700 border border-gray-600 h-24"
              placeholder="e.g., 'Count the Red Bull cans. Warn me if fewer than 5.'"
              onChange={(e) => setFormData({...formData, rule: e.target.value})}
            />
          </div>

          {/* --- ACTION BUTTONS --- */}
          <div className="flex gap-4 mt-6">
            <button 
              onClick={handleTestConnection}
              disabled={isLoading}
              className={`flex-1 py-2 rounded font-bold ${isLoading ? 'bg-gray-600' : 'bg-green-600 hover:bg-green-700'}`}
            >
              {isLoading ? "Testing AI..." : "Verify Rule & Connection"}
            </button>
            <button onClick={onClose} className="px-4 py-2 rounded bg-gray-600 hover:bg-gray-500">
              Cancel
            </button>
          </div>
        </div>

        {/* --- RESULTS AREA --- */}
        {testResult && (
          <div className="mt-6 p-4 bg-gray-900 rounded border border-green-500">
            <h3 className="text-green-400 font-bold mb-2">✓ Connection Successful!</h3>
            <p className="text-sm text-gray-400 mb-2">Gemini Analysis:</p>
            <pre className="text-xs bg-black p-2 rounded overflow-x-auto text-green-300">
              {JSON.stringify(testResult, null, 2)}
            </pre>
            <button className="w-full mt-4 py-2 bg-blue-600 rounded font-bold hover:bg-blue-500">
              Save Monitor
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AddMonitorModal;
