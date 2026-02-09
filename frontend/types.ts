export type MonitorType = 'QUANTIFIER' | 'DETECTOR' | 'PROCESS';
export type MonitorStatus = 'OK' | 'ALERT' | 'OFFLINE';

export interface Monitor {
  id: string;
  name: string;
  type: MonitorType;
  source: string;
  status: MonitorStatus;
  lastUpdate: string;
  rule: string;
  integrations: string[];
  thumbnailUrl: string;
  connection_url?: string; 
  interval?: number; // in minutes
}

// Specific Data Structures for Logs
export interface QuantifierData {
  sections: Array<{
    name: string;
    count: number;
    status: 'OK' | 'LOW' | 'HIGH';
  }>;
}

export interface DetectorData {
  checks: Array<{
    rule: string;
    pass: boolean;
  }>;
}

export interface ProcessData {
  progress: number; // 0-100
  stage: string;
  details?: string;
}

export interface LogEntry {
  id: string;
  monitorId: string;
  monitorName: string; // Denormalized for easier display
  monitorType: MonitorType;
  timestamp: string;
  data: QuantifierData | DetectorData | ProcessData;
  isAlert: boolean;
}
